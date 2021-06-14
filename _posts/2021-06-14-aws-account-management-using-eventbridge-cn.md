---
title:  用Eventbridge来管理多个AWS账号
date:   2021-06-14 11:59
ref:    aws-account-management-using-eventbridge-cn
---

本文会向大家介绍我们的多AWS账号管理解决方案. 我们已经使用这个方案有一年左右. 作为一个例子, 我们有一次通过cicd pipeline在半个小时内创建了11个AWS账号.

在我们介绍技术细节前, 我想先定义一下我们要解决的问题: 我们想要在满足安全的前提下自动化我们的AWS账号创建流程. 在任何一个公司里面, 当你需要创建新AWS账号的时候, 你可能需要和公司里的Infra工程师聊一下需求和细节. 他们可能会问你一些问题, 然后用一个自动化或者手动的方式来创建AWS账号. 然后, 他们可能会需要完成一些或自动或手动的操作, 然后把账号交付给你使用.

然而, 我们面临的处境有些不一样. 我们的AWS账号增加得很快, 我们现在大概有80个账号, 在接下来一年内可能会再增加100个左右. 如果照比较传统的模式, 我们可以写一个cicd的pipeline, 用户在跑这个pipeline的时候需要回答问题, 然后这个pipeline就会创建这个账号. 但是, 长期来看, 这不是一个好的方案, 因为所有账号的状态只在master账号里面保存, 而且这些状态没有被版本控制管理起来. 因此, 我们设计了一个DSL, 将账号的属性和设置全部定义到一个yml文件里. 开发同学想要添加AWS账号时, 需要给一个repo提一个PR, Infra同学审核合并到master后会自动触发pipeline, 自动创建账号, 等pipeline跑完的时候这个账号就创建好可以供开发同学登录使用了.

## 背景

在介绍解决方案的技术细节前, 我们先做一个背景知识的介绍, 这个部分会介绍我们的AWS使用模式, 给出一个DSL的样例, 并对Eventbridge做一个简单介绍.

### AWS Organization

每个公司使用AWS的方式都不太一样, 所以我们先聊一下我们是怎么用的. 我们是一个Fintech, 合规要求比较高. 除了一些特殊的例子(SES)外, 我们没有设置任何IAM用户. 我们用[Okta](https://www.okta.com)来管理SSO和MFA. 我们从okta登录到AWS的时候, 会执行assume role到一个特殊的`identity`账号里去. 用户在这个账号里面做不了什么事情, 只能执行另一个assume role来到另一个正常的工作账号里面去. 在`identity`账号里面, 我们所有的AWS鉴权和IAM的RBAC都是通过一个Cloudformation stack来管理的.

对于AWS Organization服务而言, 我们将Organization分成了两个OU(organization unit). 一个叫`morgue`(太平间), 用于放那些已经删除但是还没被AWS回收的账号. 另一个OU是我们内部的root, 根据scope被划分为7个子OU. 从性质来说, 我们有两种账号, 一种是工作账号, 用来跑对内测试或对外的服务. 另一种是Infra账号, 用来跑内部管理和支持服务. 我们根据用途将工作账号分成了三个子OU, 即`dev`, `standard`和`CDE`(Card Data Environment, 即信用卡环境). 对于Infra账号, 我们细分为了四个OU: `infra`, `infra-ro`, `audit`和`scp`. 只有Infra同学有权限进infra账号, 绝大多数开发都有`infra-ro`账号的只读权限, 这样他们可以看到具体这些服务是如何工作的. `audit`用于审计作用, 所有人都只有只读权限(紧急修改只能用root账号登录), `scp`用于测试应用服务控制策略(Service Control Policy).

### DSL

我们在一个yaml文件中记录了所有账号的属性和设置, 这个文件被保存到一个git repo中. 希望你能通过下面这个样例了解我们是怎么定义账号属性的:

```yaml
Default:
  create_vpc: false
  region: ap-southeast-2
  nat_gateway_count: 3
  global_region: us-east-1
  allowed_regions:
    - ap-southeast-2
    - us-east-1
    - us-west-1
    - us-west-2

Scopes:
  dev:
    organization_unit: Dev
    create_vpc: true
    nat_gateway_count: 1
    access:
      all: Admin
      rw: PowerUser,Developer

  # other scope definitions
  # ...

Accounts:
  foo:                   # An internal readable name of the account
    service: foo         # Name of the service residing in this account
    scope: dev           # Account scope that we have talked about.
    region: us-east-1    # The primary region of the account.
    create_vpc: false    # Do not create default vpc for this account.
    use_cfr: true        # Will send Cloudfront logs to a central bucket.

  # other accounts
  # ...
```

我们首先定义了全局的默认设置(默认AWS区域设为悉尼, 不为账号创建vpc等). 然后我们定义了scope层面的设置(访问控制, 对于dev账号创建vpc等). 最后是一个很长的列表, 里面的每个元素是一个字典, 对应一个AWS账号. 对于每个账号, 它会首先继承全局的默认设置, 然后继承scope层面的设置, 最后可以在账号层面覆盖全局的配置. 对于上面的例子而言, 这个内部被称为`foo`的账号不会创建vpc, 因为账号层面的`create_vpc`被设为非真.

关于上面默认AWS区域设为悉尼, 我需要补充一下, 因为AWS账号本身是相当便宜的, 所以我们会把账号当成我们要跑的服务的容器. 除非是非常特殊的例子, 一个AWS账号里只能在一个AWS区域里跑一个服务. 在这个`foo`账号里, 我们将主区域设为`us-east-1`, 因为我们预计会在里面使用Cloudfront.

### Eventbridge

[Eventbridge](https://aws.amazon.com/eventbridge/)(前身是Cloudwatch里面的事件服务)是一个方便我们做事件驱动的系统架构的AWS服务. 这个服务是无服务器(Serverless)的, 所以维护成本很低. 之前我介绍过[如何用Eventbridge来更新Buildkite构建结果的(英文)](/2020/bitbucket-build-status-from-eventbridge.html). 本文中我们用它来跨账号调用lambda函数.

作为一个例子, 当我们创建上面提到的`foo`账号时, 我们的cicd账号发给master账号的消息会类似这样:

```json
{
  'Source': 'app.infra',
  'DetailType': 'CREATE_ACCOUNT',
  'Detail': '{
    "name": "foo-nonprod-us-east-1",
    "email": "aws+foo-nonprod-us-east-1@example.com",
    "OU": "Dev",
    "tags": {
      "scope": "dev",
      "service-name": "foo",
      "environment": "nonprod",
      "region": "us-east-1",
    },
    "nonce": "687754b2-abd6-3ae6-ae2d-f98bd134512e",
    "dryrun": false
  }',
  'EventBusName': 'our-infra-bus'
}
```

随后, master账号中的一个lambda函数会被触发, 带上上面这个消息作为输入. 这个lambda会创建新AWS账号, 设置tag后将其放到要求的OU里去.

值得注意的是, 我们可以给Eventbridge定义一个策略, 这样可以控制谁能给这样Eventbridge发消息. 我们后面会详细讨论这个策略的使用.


## 解决方案

这个解决方案的要点是通过AWS API来实现对于多个AWS账号的设置和管理, 其中账号的设置被保存在一个受版本控制的文本文件里, 跨账号访问通过Eventbridge来实现. 我们在这个部分对技术细节展开讨论.

### 自举

相信你能够理解, 我们没有办法创建一个新的AWS Organization, 实现新特性, 然后让所有人从某天开始使用新账号. 我们只能循序渐进地改造现有的Organization, 添加特性, 直到我们能够用前面提到的DSL来管理现有的账号. 另外, 我们也认可从安全角度出发, 有些操作不应该被自动化(例如部署新的stackset和删除AWS账号). 所以, 整个系统自举的过程中, 我们做了下面这些操作:

- 创建用于存放Cloudformation模板和lambda的zip包的Bucket
- 部署和设置Eventbridge
- 写当前所有账号的配置文件, 写分析DSL的逻辑, 写处理各种event的lambda.
- 写一个命令能同步账号, 其结果应该是不执行任何操作.
- 在配置文件中添加一个账号, 执行前述命令, 其结果是创建一个新账号

在我们继续讨论我们设置的其他方面之前, 我想提一下我们的DSL解析逻辑. 这部分逻辑用Python完成, 暴露给shell的API类似下面这样:

```bash
./venv.sh run --action upload-lambdas
```

即, 我们有一个`venv.sh`来管理python虚拟环境相关内容, 我们通过指定action来运行对应的python函数. 另外, 我们做了一个设计上的决定, 这个命令行不应该再接受任何命令行参数, 这样强制要求我们把所有的逻辑全部放到DSL解析代码中去. 唯一的例外是`--execute`, 这个参数会将默认的dryrun变成一个真正的执行操作.

### Eventbridge设置

在上面的自举过程中, 我们说过我们需要设置Eventbridge. 如果你之前用过Eventbridge, 你就知道AWS里面没有全局性跨账号的Eventbridge. 事实上, 每个账号/区域有自己的Eventbridge, 我们要做的事情是设置策略, IAM Role和规则来把各个账号的Eventbridge连接到一起. 我们用stackset来在我们所有账号的一个区域里部署了我们的Eventbridge. 在这个stackset中, 我们主要定义了两个资源:

- AWS::Events::EventBus
- AWS::Events::EventBusPolicy

在EventBusPolicy中, 我们应该让我们的cicd账号能够发消息给所有的账号, 因此, 它应该类似:

```yaml
  EventBusPolicy:
    Type: AWS::Events::EventBusPolicy
    Properties:
      Action: events:PutEvents
      Principal: !Ref CicdAccountId
      EventBusName: !Ref EventBus
      StatementId: allow-from-cicd-event-bus
```

需要注意的是, 我们不应该偷懒而允许各个账号之间自由地发送消息. 我们在设置一个账号允许接受来自另一个账号的消息时, 我们实际上是允许这个接受方账号被发送方账号远程控制(虽然是很有限地远程控制). 如你所知, 所有账号都是平等的, 而有些账号比其他更平等, 我们对于更平等的这些账号应该更加重视. 实际的例子是你没有任何理由允许一个开发账号往master或者cicd账号发消息. 另一点经验是, 我们在这个stackset中还定义了一个日志lambda, 这个日志lambda会把Eventbridge上所有的消息全写到audit bucket里去, 这样对我们后面排查问题和安全合规都有很大帮助.

除了这个stackset中定义的规则外, 我们还需要对于特定的账号定义一些额外的规则. 对于这样的情况, 我们会手工往各个目标账号里面部署另一个stack. 例如, 为了添加创建AWS账号的lambda和对应的规则, 我们需要往master账号中部署一个stack.

### 消息的发送和接收

根据Eventbridge的特性, 我们没有办法直接做跨账号的消息发送. 我们能做的是在发送方Eventbridge上定义一个规则, 将符合条件的消息转发到另一个账号里去. 而在接收方账号里, 在Eventbridge上定义另一个规则, 当消息满足某条件时, 触发一个lambda函数. 我们来一起过一下这个过程中发生了什么事:

首先, 我们的cicd账号中的一个进程往`our-infra-bus`这个Eventbridge上发了一条消息. 注意, 这时这个消息还没有跨账号:

```json
{
  'Source': 'app.infra',
  'DetailType': 'SAMPLE_EVENT',
  'Detail': '{
    "nonce": "687754b2-abd6-3ae6-ae2d-f98bd134512e"
  }',
  'EventBusName': 'our-infra-bus'
}
```

这条消息会匹配到Eventbridge上的这条规则并转发到另一个账号里去:

```yaml
PseudoRule:
  Type: AWS::Events::Rule
  Properties:
    EventBusName: our-infra-bus
    EventPattern:
      source:
        - "app.infra"
      detail-type:
        - "SAMPLE_EVENT"
    State: ENABLED
    Targets:
      - Arn: !Ref EventBusArnFromAnotherAccount
        Id: send-to-foo-account
```

如果你对Eventbridge消息有所了解的话就知道, 我们就是简单地用`detail-type`这个值当作路由键. 这个消息的下一站是目标账号的Eventbridge, 而且会匹配到这一条规则:

```yaml
  ReceiverEndRule:
    Type: AWS::Events::Rule
    Properties:
      EventBusName: !ImportValue stackset-infra-event-bridge-name
      EventPattern:
        source:
          - "app.infra"
        account:
          - !Ref SourceAccountId
        detail-type:
          - "SAMPLE_EVENT"
      State: "ENABLED"
      Targets:
        - Arn: !GetAtt SampleLambda.Arn
          Id: run-sample-lambda
```

这样, 我们就实现了在不使用跨账号assume-role的前提下跨账号调用lambda.

下面几点需要注意:

1. 如果在Eventbridge策略中定义了允许来自另一个账号的消息, 则这个账号发送消息是不需要额外的IAM Role, 但是如果我们允许来自AWS Organization的各个账号的消息, 则各个账号在发送消息时需要使用额外的IAM Role.
2. Eventbridge会保证至少一次递达. 这意味着你需要有一些验证的逻辑来保证操作的幂等性.
3. 按照lambda的默认配置, 如果lambda执行失败则lambda会被重试. 第一次失败后会等待一分钟后重试第一次, 然后在第二次失败后等待两分钟后重试第二次. 所以你还是得想办法保证你的lambda执行是幂等的. 另外, lambda的这个配置是可以配置的, 如果你需要, 你也可以取消这样的重试.

我们消息发送就讲到这儿, 接下来讲讲接收消息. 如果你仔细想想, 你会知道, 你没有办法用Eventbridge来实现一个经典的请求/响应模型. 消息应该触发一些东西, 但是很难用简单地办法把响应传递回给发送方. 我们的解决方案是将响应发送到发送方账号的一个SQS里去, 让消息发送方不断去轮询, 看有没有响应回来. 一个真实的例子是, 在我们的账号创建流程中, 我们需要从master账号拿到当前账号的列表. 从实现细节上, 我们在cicd账号中的一个进程会往master账号发一个消息, master中的这个lambda拿到信息后会往master的Eventbridge上发一条消息, 这条消息会匹配到一条规则, 这条规则会把这条消息传递回cicd账号, 在那儿匹配到另一条规则, 从而进入到SQS中, 直到被前面说的cicd中的那个进程轮询获取到.

关于消息的接收, 下面几点需要注意:

1. 如果不是万不得已, 不要使用这一设计模式. Eventbridge使用的是事件驱动的模型, 和传统的请求/响应模型不太搭. 绝大多数时候, 更适合的做法是发了不管.
2. 在允许一个账号接收来自另一个账号的消息前, 请再三确认. 尤其是低等级的账号(比如dev)往高等级的账号发送内容, 绝对不应该被允许.
3. 请在请求响应的消息里带上一个uuid的token, 这样这个进程能够有针对性地在队列中获取它需要的消息.

## 案例分析

关于我们的设置我们已经聊得很多很让人晕晕入睡了, 下面结合案例来说一下我们是怎么管理我们的多AWS账号环境的.

### 主pipeline

首先说下我们这个工作里最主要的特性: 我们如何创建新AWS账号.

在一个PR被merge后, 触发运行一个主pipeline. 这个pipeline首先会做一些基本的检查, 比如检查DSL语法是否正确, Cloudformation模板是否合乎我们的要求等. 然后这个主pipeline里会跑一个`sync-accounts`的命令. 这个命令会往master账号发一条消息, 触发一个master账号里的lambda, 列出当前Organization里所有的账号, 并返回给cicd账号里的SQS. `sync-accounts`命令会轮询这个SQS, 拿到这个响应后和本地配置文件进行对比, 确认是否要创建新账号, 并确定这些账号的设置要求. 然后, 我们会再往master账号发一个或多个`CREATE_ACCOUNT`消息, 这个请求会创建账号并将其移入对应的OU(Organization Unit).

我们将这个账号移入对应的OU后, 我们已部署到这个OU的stackset会开始干活, 给这个账号添加适当的stack instance. 这个过程我们不详述了, 我们还是回头看看cicd账号里发生了什么事情. 主pipeline里下一个步骤是重新生成一些Cloudformation的模板并上传到Bucket里去. 例如, 我们需要更新`identity`账号里的一个stack, 来允许用户访问和使用这个新账号. 我们会在主pipeline的后续步骤里更新这个stack, 但是我们需要重新生成这个模板并放到合适的地方去.

接下来, 我们会在cicd账号中添加一条规则, 允许我们将消息发送到这个新账号, 这个规则的创建依赖于新账号中eventbridge的创建, 所以我们得在cicd账号中发消息给master账号, 确认对应的stack instance是否已被部署好. 这一步完成后, 我们就可以在cicd账号中添加对应的规则了.

到了这个时候, 新账号中的Eventbridge已被创建好, cicd账号可以给所有的账号发消息, 而且Cloudformation模板已更新. 我们接下来会并行执行下面几个操作:

1. 发消息给各个账号, 更新SSM条目. 在各个账号里, 我们有`/pub`这个命名空间用来放全局性的值.
2. 更新`identity`账号里的stack, 允许访问新账号.
3. (按需)给新账号创建一个VPC.
4. 更新logging账号中的bucket policy允许来自这个新账号的Cloudfront/WAF/ELB/apigw日志.

所有这些操作做完后, 新账号就可以使用了.

### DNS管理

我们在一个单独的AWS账号里中央管理我们的域名, 我们将这个账号称为dns账号. 我们这样做是出于安全考虑, 因为这样如果一个账号被拿到了管理员权限, 入侵者能修改的域名也很有限. 然后, 这样的设定也让我们的SSL证书验证稍困难了一些, 之前在单个账号能完成的操作现在得需要跨账号消息的方式实现.

在Eventbridge设置上, 我们需要让Organization里每个AWS账号都能给dns账号发消息. 在dns账号中, 我们除了全局的日志lambda外, 只处理下面三类消息:

- 通过委任(delegation), 创建DNS子zone
- 管理nlb/Cloudfront/apigw的alias记录
- 创建ssl证书中的DNS验证记录

我们为每个AWS账号都创建了一个公开DNS zone, 这样可以方便快速发布一个服务. 这个子zone所用到的顶级域名不是我们公开提供服务的.com域名, 我们也没有做任何宣传, 本身就是供内部使用的. 当我们新创建AWS账户的时候, 每个账号会往dns账号发一个请求, 创建这个DNS委任. 这个操作是通过Cloudformation的自定义资源(custom resource)完成的. 在这个lambda的逻辑里面, 我们还会为这个子zone创建一个随机A记录, 并轮询DNS来验证这个随机记录是否能够被成功解析. 如果解析成功, 说明这个委任机制是正常工作的.

我们允许每个账号给dns账号发请求来修改DNS记录, 但是这个操作会受到dns账号中的lambda内部白名单限制. 例如, 我们对外的主服务域名只能被某一个账号修改, 其他所有账号都没有办法修改这个记录. 在lambda实现上, 我们会去读取dns账号中的ssm条目, 这些条目是在我们的主配置文件中定义的. 对于每个账号, 我们定义了一个名为`allowed_dns_domains`的可选字段. 如果某账号定义了这一字段, 我们就会在主pipeline中把这个记录写到dns账号的ssm中去.

### 日志配置

我们有一个单独的AWS账号用来归集所有的ELB/Apigw/Cloudfront/WAF日志, 它被我们称为logging账号. 当我们创建了一个新AWS账号时, 我们得修改logging账号里S3的bucket policy, 允许来自新账号的日志写入. 出于安全考虑, 这个logging账号被我们放进了`audit`这个OU, 所有人都只有只读权限. 在我们允许自动修改前, 这个账号里的bucket policy有类型下面这样的定义:

```yaml
- Sid: deny-modification
  Effect: Deny
  Principal: '*'
  Action:
    - 's3:Delete*'
    - 's3:PutBucket*'
  Resource:
    - !Sub 'arn:aws:s3:::${BucketName}'
    - !Sub 'arn:aws:s3:::${BucketName}/*'
```

即, 禁止任何人执行删除或修改bucket policy的操作. 为了实现自动修改, 我们将它改为:

```yaml
- Sid: deny-modification
  Effect: Deny
  NotPrincipal:
    AWS:
      - !Sub "arn:aws:iam::${AWS::AccountId}:role/update-s3-stacks-role"
      - !Sub "arn:aws:sts::${AWS::AccountId}:assumed-role/update-s3-stacks-role/AWSCloudFormation"
  Action:
    - 's3:Delete*'
    - 's3:PutBucket*'
  Resource:
    - !Sub 'arn:aws:s3:::${CfrLogsBucket}'
    - !Sub 'arn:aws:s3:::${CfrLogsBucket}/*'
```

即, 我们将我们自动更新的lambda所使用的IAM Role放进了白名单, 只允许来自这个白名单的修改. 另外, 在lambda里面我们写死了Cloudformation模板的路径. 因此, 如果要破坏这个机制, 要么这个人能够拿到我们infra账号的管理员权限来修改源头模板, 要么这个人能够拿到这个logging账号的root权限来修改里面的资源. 无论是哪种情况, 我们要面临的问题都比这个bucket policy被修改更大.

### 中央管理ECR

我们在cicd账号里通过Cloudformation中央管理了我们的ECR(AWS的docker镜像服务). 大致思路是用一个DSL来定义每一个repo的生命周期策略和访问权限, 然后解析这个DSL并生成一个Cloudformation模板. 这个DSL类似:

```yaml
  - name: foo-bar-image
    policies:
      - dev-: "7 days"
      - untagged: "7 days"
    permissions:
      pull:
        accounts: nonprod
        services: foo
    repository-tags:
      description: Foo Service
```

之前, 这个项目有一个单独的repo. 后来我们将这两个项目合并了, 最大的好处是我们添加了上面pull里面的services字段, 这样我们给某个服务新添加了一个账号后, 我们不需要修改配置文件就能够重新渲染模板来允许新账号拿到ECR里对应Repository的镜像.

### 应用服务控制策略(Service Control Policy, SCP)

我们的SCP也是通过代码来管理的. 所有的SCP策略文件被保存到同一个目录里. 在项目的主配置文件里, 我们在OU层面上定义了每个OU启用了哪些策略. 而在主pipeline里面, 我们也有一个单独的步骤来将我们配置文件中定义的SCP同步到master账号里去. 请注意, SCP是危险程度比较高的操作, 请在测试后再应用(这也是为什么我们有一个单独的scp OU).

## 总结

本文我们简单介绍了我们是如何通过代码来管理AWS多账号的. 如果有问题/建议, 请联系我, 我乐于倾听和回答.