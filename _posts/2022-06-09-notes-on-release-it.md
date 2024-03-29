---
title:  Release it笔记
date:   2022-06-11 15:22
ref:    notes-on-release-it
---

[Release it](https://learning.oreilly.com/library/view/release-it-2nd/9781680504552/)是我年初读完后一直想回顾的一本书. 书里面除了常见的讲道理, 列要点, 还絮絮叨叨地讲了一些生产环境挂掉的例子. 下面列一些读书笔记和故障报告, 以效它山之石.


### 案例: 航空公司登机牌系统故障

航空公司的架构很简单, 用户请求先到负载均衡器, 然后到多台后台业务逻辑服务器, 再往后到两台主从数据库服务器. 服务有监控能够自动切换数据库和更替故障的业务逻辑服务器. 有一天晚上一个维护人员做了一个常规的数据库主从切换操作, 操作后请求返回正常, 维护人员观察无异常后就去休息了. 然而两个小时后服务挂了, 导致美国所有这个航司的登机服务都不能工作. 程序员重启了业务服务器, 故障恢复了, 整个故障时间是三个小时.

经分析, 故障原因是在处理数据库连接时, 程序员在有异常的时候做了处理, 停止当前的查询并关闭连接. 但是程序员没有注意停止当前的查询的时候也会触发同一个异常(当数据库主从切换时), 这导致数据库连接不会被正常释放. 过了一段时间后, 连接池里所有的连接都被污染, 这个时候业务逻辑服务器就没法做数据库查询了.

教训是服务应该期待其他服务挂掉, 并充分保护自己不会被其他服务的故障波及. 最简单的, 做外部调用的时候要加上超时, 这样可以避免无限制的等待; 适当的地方添加消息队列也会有帮助.


### 案例: 数据库连接丢失故障

一个三层应用, 业务逻辑服务器启动时会起一个连接池, 每个连接都连到数据库. 每天五点请求量上来后都会挂, 重启就好了, 直到第二天同一时间. 从业务服到数据库的网络连接是正常的.

故障原因是业务服务器到数据库服务器间有一个防火墙, 防火墙上有个每个小时自动杀空置连接的功能. 所以当业务不太繁忙的时候, 可能只有一两个连接还是真正存活的. 五点请求上量后单个连接顶不住就挂了. 当防火墙单方面丢弃这个连接以后, 两边的服务器没收到任何数据包, 所以还会认为这个连接仍然存在且健康. 当试图用这个连接写数据的时候, 经过20-30分钟的超时后才会报错说连接已受损. 而读数据则是有无限长的超时.

修复方式是Oracle数据库有一个探测死连接的功能, 原理是定时发心跳包给客户端看客户端是否仍在正常工作. 这个心跳包能重置防火墙上的上次数据流量时间, 避免这个连接被关闭.


### Reddit扩缩容故障

官方故障说明在[这儿](https://www.reddit.com/r/announcements/comments/4y0m56/why_reddit_was_down_on_aug_11/). 迁移一个服务时, 为了避免自动扩缩容导致系统挂掉, 程序员手工关掉了自动扩缩容系统. 后续一个软件更新系统发现这儿有一个人肉修改, 重新启用了自动扩缩容系统, 导致系统故障.

作者认为应该在自动扩缩容系统中加上限制条件, 避免背刺:

1. 如果机器人发现80%以上的系统都故障了, 更可能是观察者自己有问题
2. 扩容要快, 缩容要慢. 新起机器比关闭机器要安全得多.
3. 扩缩容系统发现的差异太大时, 做出变化前应该要求人肉确认.
4. 不应该无限制扩容
5. 扩容要加上冷却机制, 避免因下达扩容命令到真正机器可用之间的时间差导致扩容指令被执行多次导致过度扩容.


### 数据表突然增加行数故障

一个大型三层应用, 突然有一天逻辑服各种报障, 往往重启加载缓存都还没完成就又挂了. 后来查实是一个本来有几行数据的一个小数据库表突然多了一千万行数据, 而之前写的时候没加任何limit, 导致内存溢出. 这个故障本来没什么, 作者调查的顺序在我看挺中规中矩而且有不少java直接相关的专门信息, 所以我就从略了. 作者说这种情况是因为没有很好的限制数据库查询结果而导致的. 其实不仅仅是数据库可能有这样的情况, 如果没有良好设计的API也可能有这样的自杀式查询.

另外, 虽然作者没有提及, 但是我觉得没有一个变更管理系统也是让人对故障发生的源头毫无头绪的直接原因. 这种数据库的变更会马上导致新启动的逻辑服无法正常执行完加载逻辑, 而如果那个时候能快速将故障原因定位出来, 也可以降低因服务不可用而造成的损失.


### AWS S3故障

故障报告在[这儿](https://aws.amazon.com/message/41926/). 当年这个故障出来的时候, 我觉得这个故障报告值得重读. 当时读了几遍, 几年后的今天, 又重读了几遍. 具体这个案例我就不再多加讨论了, 本身评论已经很多了. 除了一点, 也是我很赞同作者的一点, 整个故障报告里面, 没有一次提到人为错误, 都是说系统错误, 虽然整个问题的起因实际上是一个人为操作故障. 这不是文过饰非, 更不是为尊者讳, 而是将整个系统的操作人员, 报告脚本(playbook)提供的API, 包括系统本身在接受到错误输入时的行为放到一起来讨论和总结.


### 含糊不清日志事件

谢天谢地这终于不是一个故障了. 作者有一次和一个运维聊天时, 运维收到一台报警日志消息("Data channel lifetime limit reached. Reset required."), 然后运维上线做了一次数据库主从切换. 而事实上, 这条日志就是作者的代码写出来的, 本意是一个加密通道的密钥使用时间过长, 需要重置(而且服务本身会重置). 作者指出, 这条日志本身应该说清应该由谁来执行重置的操作, 这样就能很大程度上避免这个问题了. 另外, 这条日志本身是作者加入的一个调试, 只是想看一下运行时这个重置多久发生一次, 他后面忘记去掉了. 我觉得在生产环境上线前, 审查一遍所有的日志, 去掉不需要的日志, 保证每条日志应该本身能够解释自己是在做什么, 避免歧义.

当然, 说这不是一个故障也是不太准确的, 这个运维每周会在最繁忙的时段做一次主从切换, 自然会带来短暂的downtime.


### Specification不完善事件

作者讨论了一个案例, 两个组分布在两个大陆. 为了合作, 他们讨论并通过了一个很完善的Specification. 大多数情况下, 这个工作就到此为止了. 但是作者他们当时更进了一步, 写了一个完善的测试样例. 在编写这个测试样例的过程中, 他们又发现了相当多的边界条件导致的Specification的瑕疵. 整个测试案例跑完了之后, 他们对整个系统的运行有了更好的信心, 后面系统上线也很顺利.


### 自动化测试的成本核算

如果有自动化的测试流水线(pipeline), 我们可以获得很多好处, 不赘述. 但是直接的好处是我们能够避免生产环境挂掉带来的损失. 比如测试流水线的开发也许需要两个月薪一万的程序员一个月的时间开发, 总开发成本是2万. 后面可能只需要偶尔的维护, 比如每个月需要一个这样的程序员花三天时间在维护上, 即每个月的维护成本大概是两千. 再看看运行成本, 如果我们每次运行这个测试流程的成本是10块, 平均每天运行50次, 这样每个月运行成本大概也是两千. 我们做一个合理的假设, 如果这个测试流水线的开发能够降低我们的故障率, 每年减少的服务故障时间是10小时(很保守的估计). 所以, 不提其他的好处, 如果我们的服务每小时收益达到五千元, 那么一年的减损就能覆盖掉运行和维护成本. 这种时候就应该投资来做自动化测试.

真实世界中往往没有这么简单的非此即彼, 测试往往是通过其他方式运行, 开发成本和运维成本不一. 但是从成本核算的角度讲, 一个理性的管理人员应该跟随收入的SLA/SLO来预估在开发和运维上的开销. 合理调配资源实现收益的最大化.


### 系统是怎么挂的

整本书对我感触最大的一句话是: 每个挂掉的系统都是因为某个地方有一个队列没正常工作.

无论是IO队列, TCP队列, 线程池, 软硬限制(limit), 包括外部队列服务. 如果能够找到这个故障的队列并解决, 就可以解决系统的故障.


### TCP网络连接故障表

下面是书中列出的所有TCP异常状况, 服务可以按需处理:

- TCP连接可以被拒
- TCP连接可能超时
- 对面可能回复SYN/ACK后再也不见
- 对面或者GFW可能会发RST
- 对面可能会指定一个接收窗口, 但是不发还足够的数据
- 连接可能建立, 但是对面不发任何数据
- 连接建立, 但是可能丢包造成重传延迟
- 连接建立, 但是对面一直不ACK收到的包, 导致无限重传
- 服务收到请求, 并发回响应头, 但是一直不发内容
- 服务可能每三十秒发一字节响应
- 服务可能发回一个HTML而不是json
- 服务可能发回比我们期待大得多的响应
- 服务可能以各种方式拒绝认证请求