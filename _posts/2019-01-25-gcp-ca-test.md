---
title:  "GCP-CA考试备考心得"
date:   2019-01-25 23:04 +1100
ref:    gcp-ca-test
---

这周过了GCP-CA考试, 全称应该是谷歌云平台职业云架构师(Google Cloud Platform Professional Cloud Architect)资格证书考试. 在这儿写写我是怎么准备的, 希望对人有帮助.

先大致介绍下我的背景: 我自己天天做和AWS相关的东西, 谷歌的云平台和AWS在很多地方是相同或至少是相通的, 这给我的备考带来了很大的便利. 例如, 对于Compute Engine我就基本没看, 因为我天天用. Deployment Manager基本就是一个富人版的Cloudformation, 所以了解下小区别后也不用看了. 除此之外, 我供职的单位和Google有合作关系, 我们能报名参加一个Google组织的Dash-to-Cert活动, 在一个月时间内, 每周会有Google工程师给我们讲GCP考试学习以及应考的要点. 附带的, 也会要求我们上一个Coursea上的系列课程. 这些课程和讲解也给我的应考打下了很好的基础. 所以我现在过了考试可以臭屁说这个证书比较水, 没难度. 但是一个没有GCP基础的人或甚至一个没有云计算基础的人要备考, 可能并不算容易.

下面是我应考前准备的要点们, 主要是记录一些和AWS不一致, 而且我没有记太清楚的地方.

* 项目间通信走公网，即使同region, 项目内通信走Google内网，即使跨region
* 子网可以跨zone
* IAM role types: primitive/predefined/custom
* Resource policy是parent和当前资源的并集, Less restrictive policy from parent override more restrictive resource policy.
* 网络有两种模式: auto mode和custom mode. 选了custom mode就不能退回到auto mode了
* 项目可以共享vpc, 也可以通过vpc network peering来连接vpc而不需借助公网IP
* gsuite不是必要的, gcp自己不管理用户和组(但管理service account), 不用gsuite可以用cloud identity.
* BigTable应用场景: 大于1T的数据量 且 大量写入 且 读写时延小于十毫秒
* 数据写入cloud storage的几种方式: storage transfer service(general), google transfer appliance(从g借一个服务器), offline media import(物理硬盘送到第三方负责上传)
* cloud sql的特性限制们: (最大10TB/最大4k连接/不能跨区域), 不行的话就spanner
* cloud endpoint 只能指到gcp中的资源，无法指回onprem
* Datastore和bigtable不能跨region
* 执行安全扫描前不需要通知GCP.
* 公私云网络连接:
  1. vpn: 可以有动态路由更新cloud router, gcp提供入口
  2. Direct peering, 限制是全球只有70多个地点支持这种连接, 优点是网速快, 直接连到gcp
  3. Carriers peering: 通过isp实现direct peering
  4. peering总是通过软件实现的, interconnect是物理连接.

除了上面说到的Dash-to-Cert和Coursea课程, 我另外还看完了一本Packt家的和GCP相关的书(Google Cloud Platform for Architects, ISBN: 978-1-78883-430-8). 原因是Dash-to-Cert和Coursea的课程距离考试的时间比较久了, 需要温故一下. 这本400多页, 但是读起来很快. 我大概每天看50页. 看完后再找到Dash-to-Cert的视频重看了一遍. 最后再做了下官方的模拟题就去考试了. 就我个人感觉, 官方模拟题比实际考试稍简单一点. 模拟题里会有案例分析题, 所使用的案例们在GCP网站可以看到. 我当时没想着去细看, 因为我认为考试时应该会有全新的案例分析. 但是考试时发现试卷中的案例分析用的仍是那些案例. 所以强烈推荐把这几个案例分析多看几遍, 多想想要求和实现.

最后, 说下应考心得. 考试形式是在电脑上完成50道选择题, 大都是单选, 有少量多选(少于5题). 考试时间是120分钟. 整个阅读量很大, 所以我花了65分钟才完成. 考试过程中可以标注那些不太确定的题目, 回头也方便检查. 我大概花了15分钟来重新读那些不太确定的题目并做出选择. 另外最后又花了20分钟来检查所有的50道题, 这一次只读选项, 不读题干. 完成合这一遍后我就提前提交答案了. 提交后当场就公布了provisional的成绩, 又过了一天就拿到正式的资格证书了.
