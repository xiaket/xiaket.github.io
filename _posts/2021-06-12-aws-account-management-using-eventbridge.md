---
title:  AWS account management using eventbridge
date:   2021-06-12 17:03
lang:   en
ref:    aws-account-management-using-eventbridge
---

In this article, we are going to present how we manage our AWS accounts via code. We have been running this solution for around a year now, and in one occasion we created 11 new AWS accounts in around 30 mintues in the CICD process.

Before we dive into the technical details, I would like to define the problem that we are aiming to solve here: we want to automate the AWS account creation process in a safe way. In any company, when you want to create a new AWS account, you'll need to discuss the requirements/details with your infrastructure experts. They would probably ask you a few questions, then do the account creation either via your internal account vending machine or AWS Control Tower or manually. After that, this expert would probably need to do some more manual work to make sure that this account is ready for you to get in.

However, we are in a different situation in that the number of our AWS accounts are fast-growing. We now have around 80 AWS accounts and are expecting 100 more in the coming year. We can easily write a pipeline that asks user for input and create the aws account accordingly. However,
in the long term, we would like to have the account attributes and settings stored so we can track the change over time. Hence, it is logical to use a DSL(Domain Specific Language) that describes the attributes and settings. In this way, we will have a process that the developers can create a PR to change the config in a git repo, we will then review the PR. After the PR gets into master, a pipeline run will bring a new AWS account to life and the developers can start using it. As the title suggests, we've achieved this using AWS eventbridge.

## Background

We wish to add some more technical backgrounds before we talk about our solution. This section will include our AWS setup, a sample account definition in our DSL, and a primer in eventbridge.

### AWS organization

Each organization uses AWS differently, so I would like to introduce you to our infrastructure setup first. Working in a Fintech company, we are in a highly regulated environment. Apart from some corner cases(SES), we don't have any IAM users. We are using [Okta](https://www.okta.com) as our SSO/MFA provider. When we login to AWS via Okta, we assume a role in a special AWS account that we called `identity`. From this account, we then do another assume-role to the account that you are going. So all our AWS access and RBAC are defined as a Cloudformation stack that provisions different IAM roles.

In AWS organization land, we divide our organization at the top level into two organization units(OU). One is called `morgue` which is for accounts that we are going to delete soon or accounts that we had deleted and waiting for them to fade away. The other OU is our internal root OU, which we have subdivided into 7 different OUs by scope. We grouped our workload accounts by their usage and compliance requirements into three scopes: `dev`, `standard`, and `CDE`(Card Data Environment). For non-workload accounts, we have four scopes, and they are: `infra`, `infra-ro`, `audit`, and `scp`. Only SRE(Service Reliability Engineer) team has PowerUser and above access in `infra` accounts, most members in the dev team have ReadOnly access in `infra-ro` accounts so they can understand the internal machinery, `audit` is for auditing purposes and is highly constrained, and `scp` is for service control policy testing.

### Account definition DSL

We define a list of AWS accounts in a yml file that is maintained in a git repository. From a very high level overview, this main configuration file may look like:

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

  # other account definitions
  # ...
```

We first define organization level default values(Defaulting AWS region to Sydney, do not create vpc, etc.). Then we define scope level options(AWS access pattern, create vpc for dev accounts, etc.). After that, it is a long list of AWS account as a dictionary. For each account, it will inherit the default options from the root level and then OU level options, also we can do the override at the account level. In the above example, this account with internal name `foo` will inherit a bunch of other flags from `Default` and the `dev` scope. However, as we have set `create_vpc` to `false` at the account level, we will not create a VPC.

Regarding the region thing defined at the account level, we have an internal rule that unless it's a very special case, we do not allow any service running in multiple AWS regions. Our default region is define at top level to `ap-southeast-2` and is overriden to `us-east-1` because of Cloudfront requirements.

### Eventbridge

[Eventbridge](https://aws.amazon.com/eventbridge/)(previously Cloudwatch events) is an AWS service that makes it easy to deliver messages to the right audience. It's serverless so we don't have to care about the maintenance. Previously, I had [used eventbridge to send bitbucket build status updates from partner eventbridge](/2020/bitbucket-build-status-from-eventbridge.html). In this article, we are using eventbridge to do cross-account lambda calls without cross account IAM roles.

As an example, to create the `foo` AWS account we listed earlier, the cicd account will send the following message to our master account:

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

Then, a lambda in our master account will get triggered, take the event as input, create the new AWS account, tag it, and drop it off into the right OU.

It is also worth noting that we can define an eventbus policy that controls which AWS account(s) can send messages to which eventbus. We'll talk more about this control later in this article.


## The solution

We use AWS API to manage a multi-account setup where resource deployment is done via stacksets and cross account access is done via eventbridge. We are going to discuss how we did the setup of the solution and how it works in depth in this section.

### Bootstrap

As you can understand, we cannot create a whole new organization and build it then ask everyone to switch, we will need to build the new features in our old AWS organization. We also acknowledged that some operations have to be done manually for security reasons. One of the very first manual operation that we've done is to create an S3 bucket for artifact(cloudformation template, lambda zips) storage. Due to Cloudformation restriction on lambda zip, we had actually created not one S3 bucket, but 4 buckets, as we have 4 regions that we had business in. We then put the Cloudformation template into the newly created S3 buckets. We also started a Python module that can deploy this stack. This completes our bootstrap process.

Before we continue with other aspects of our setup, I would like to talk a bit more about the Python module. From the outside, we provide an cli level API that looks like this:

```bash
./venv.sh run --action upload-lambdas
```

That is, we have a bash script to manage the python virtual environment, and we specify the action we want to run as an argument. This looks common enough, but I would like to say that we've made a decision to not to accept any other flags, that means all parameters of the action must be defined in the code. The only exception is the `--execute` flag, which turns a harmless dryrun into a real operation.

### Eventbridge setup.

Next thing we want to do is of course setup the eventbridge. If you have used eventbridge before, you will know that there's no global cross account eventbus. Instead, each account/region can have it's own eventbridge. And we will add some policies/roles/rules to connect these eventbuses together. We have deployed eventbuses in a stackset that is deployed to all accounts in a single region.

In this stackset, we have defined the following resources, as these resources should exist in all accounts.

- AWS::Events::EventBus
- AWS::Events::EventBusPolicy

In the event bus policy, we should allow our CICD account to send messages to all accounts, which means the EventBusPolicy should look like:

```yaml
  EventBusPolicy:
    Type: AWS::Events::EventBusPolicy
    Properties:
      Action: events:PutEvents
      Principal: !Ref CicdAccountId
      EventBusName: !Ref EventBus
      StatementId: allow-from-cicd-event-bus
```

The tip here is use minimal permission setup that works. Unless this is truely a special case, the account should only accept eventbus message from the cicd account. Another tip that we can offer is to have a logging lambda that matches every event on the eventbus and logs it to an S3 bucket in the audit account

We had deliberately kept this stackset minimal. And we have defined another stackset to deliver the common rules, which allows us to deploy a vpc on demand and distribute some SSM entries to the account.

Apart from the common event rules that we have defined in the stackset, we need a few more event handlers in various special accounts. In these cases, we will create a stack in the bespoke account manually. We will talk a bit more about these handlers in some individual accounts later in this article.

### Sending & Receiving Message

With current eventbridge feature set, we cannot do cross account message sending directly. That is, we cannot send a message directly to trigger a lambda in another account. Instead, we must have a rule on the eventbus to forward the message to the bespoke account, and on the receiver end, match the message with some rule and then trigger a lambda. In this section, I will walk you through the whole process.

First, we send a message that looks like:

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

This message will be sent to the `our-infra-bus` event bus and will go nowhere unless we have a rule that matches it like this:

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

We are simply using the `detail-type` as routing key to send message to the right account. The next stop of our `SAMPLE_EVENT` is the eventbus in the destination account, and will match this rule:

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

In this way, the message will trigger the destination lambda.

A few caveats here:

1. If in the event bus policy, we have explicitly allowed message from another account ID, we don't need a role in the event rule to send the message to that account. However, if we are allowing message from within an organization, we need an explicit IAM role to send the message from the source account to the destination account.
2. Eventbus will have at least once delivery. That means you should have some validation logic or business logic in your lambda to achieve idempotency.
3. By default, lambda will auto-retry if it failed. We had observed that if the lambda failed, an automatic retry will happen after 1 minute and then another retry in another 2 minutes(This is the default behaviour of AWS lambda). In many cases, this is a good thing because we would want this behaviour. But again, you need to pay attention to your idempotency. Also, this is configurable, so you can opt out in the lambda settings.

Enough about sending, let's talk about receiving message. If you think about it, it is not natural to send a response back using eventbridge. Events should trigger something but there's no simple way to send a response back to the event caller. The best thing we can do is to send the response back to an SQS, and have the calling process polling the queue for new messages. A real world example is, when we run the accounts creation pipeline, we need to get the list of AWS accounts from our master account. This is done by a process in our CICD account sending a message to our master account, and the lambda listing accounts in master account send a message back to the eventbridge, with a rule matching it and forward that to the cicd account eventbus and end up in the SQS.

A few notes here:

1. Please do not consider a request/response model unless you definitely need it. Most of the time, the fire-and-forget fashion is better.
2. Please think twice when you allow an account to receive a message from another account. If the sending account is compromised, you will risk running things in the receiving account.
3. Please have a nonce token in the requesting message, and the response will send the same token back so we can pick up the right message in the queue.

## Case studies

We've talked long and ardurously about our setup, let's now direct our focus to a few case studies and hopefully we can demonstrate the strength of this event-driven setup.


### The main pipeline

Let's talk about the prime feature of this pipeline first: how do we create AWS account(s) with this setup?

First, we will run a `sync-accounts` command in our CICD account, which will send a message to master account and trigger a lambda in that will list all AWS accounts with their tags and send it back to the queue in CICD account. `sync-accounts` will poll the message and determine how many accounts do we want to create/delete. After that, we will send a `CREATE_ACCOUNT` request to the master account, which then will create the new account and move it to the right OU.

Once we've finished creating the account, a lot of stack instances will be created from various stacksets in master account, they will wait for each other when needed, but this horse race is less interesting than what will happen in our CICD account. The next command that will happen is to re-render some of the cloudformation templates from jinja templates and upload them to the artifact buckets. For example, we'll need to update the template that defines the stack in 'identity' account to allow access to this new account via assume role.

Next, we will add new rules in cicd account to allow us to send message to the new account(Remember we have the event bus and the event policies, but not the event rule). However, this has an dependency on the deployment of the common event rules stackset. So we will again send a message to master account and wait till that stack instance has been deployed in the new account. Once that's done, we will continue our process in CICD account and create the new forward rule.

At this point in time, we have the eventbus created in the new account, and we have the latest Cloudformation template uploaded to the artifact buckets, so we can do the following things in parallel:

1. create SSM entries including account tags and some other global info to the new account.
2. update the IAM mapping stack in `identity` account to allow access to the new account.
3. Deploy a vpc in the new account. However, it is up to the account to determine whether it needs a vpc so the new account may not receive this `CREATE_VPC` message after all.
4. Update the S3 bucket stacks in logs account to allow Cloudfront/WAF logs ingess.

After all these process runs through, the new AWS account is ready to use.


### DNS management

We manage all our domain names centrally, and we call it our DNS account. We consider this to be a good security feature because even someone had gained administrative access to one of our accounts, he/she will not to change other dns entries than allowed for that account. However, this had made our SSL certificate validation a bit hard, we will have to send a message to the dns account to update those entries.

For the eventbridge setup, we will need to allow every account in the organization to send message to this dns account. But apart from the logging lambda we have universally enabled, we will only trigger a lambda on the following three event types from all the accounts:

- create dns delegation
- manage nlb/cloudfront/apigw alias
- manage dns validation record

We created a public dns zone for every account and that is somehow linked to the account number, so whenever someone want to expose some test dns record he/she can always use this semi-internal zone. We allows each account to send a request to modify dns entry to either create an alias record or create a CNAME record for ssl certificate validation, but these two are subject to access control in the dns account. For example, we would only allow account A to create a record for some domain name a.example.com, but account A cannot create record as b.example.com. This access control is defined in our DSL file as `allowed_dns_domains`, and they are exported to dns account as ssm. Our cicd account will push these ssm entries down in the master pipeline.

### logging updates

We have an account for ELB/ApiGW/Cloudfront/WAF logs, when a new account need to send the logs to this account, we need to update the bucket policies in this account to allow log ingress. As this account is in our `audit` scope, we had used a service role in this stack update. In most cases, we may want to protect an S3 bucket from modification/deletion by defining a policy that looks like this:

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

In order to make the bucket policy update work, we have altered this section to:

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

That is, we had whitelisted the roles used by the updater lambda to allow incoming modification. And of course, we have pre-defined the Cloudformation template path. What will happen is, we will send a message to this logs account, where we have a lambda that will run and use the service role to update the S3 bucket policy.

### ECR

We manage our ECR repository centrally in our cicd account via Cloudformation, this used to be a separate project but it had since merged into our DSL repo. The general idea is to have another DSL that defines the life cycle policy and the access policy for the ECR. The DSL will look like this:

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

With a list of repositories defined in the file, we will generate a Cloudformation template and deploy it into our cicd account. The best part is since we are allowing the aws account that runs `foo` service to pull the image, when we add a new account that runs the `foo` service, the access policy will be updated to include the new account.

### Service Control Policies

We are also managing our service control policies in this repo, the service control policies are defined in a directory, with the policy name tied to the organization unit that needs this policy. In the main pipeline, we have a step to synchronized what we have defined in our repo with what's enabled in the OU. Please note that it is better to test the service control policy before you deploy it, and that's exactly why we have an organization unit named SCP.

## Summary

In this article, we discussed our way to manage aws accounts/aws organization via code. Please reach out to me if you have any questions/suggestions! We’ll be happy to hear from you and help you out.