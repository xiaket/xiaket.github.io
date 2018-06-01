---
title:  "ansible请求处理"
date:   2018-05-23 20:33 +1000
lang:   zh-cn
ref:    ansible-request-handling
---

# 题记

这篇文章写于两年前, 主要工作是在网易游戏工作的时候完成的. 理论上知识产权应该属于网易, 不过据我所知, 至少我之前所在的网易游戏部也没有大规模使用Ansible. 而且时过境迁, Ansible也有一些版本变迁, 所以我还是全文贴出, 希望能够帮到一些人.

我半年前在一个本地Ansible Meetup上做过一个演讲, 介绍当时这一块的工作, slide可以在[这儿](https://speakerdeck.com/xiaket/a-glimpse-of-ansible-internals)找到.

以下为原文.

# 缘起

更新到2.0后, ansible有了一些代码结构上的变化, 之前可以用的插件也大都失效了. 为了能够理解ansible对请求的处理, 我们深入分析了ansible的代码, 总结出这样一篇文章.

# 通过Python API来运行

我们的一个目的是通过Python而不是通过调用系统命令的方式来运行Ansible, 我们的出发点是官方文档中的[Python API 2.0](http://docs.ansible.com/ansible/developing_api.html#id3)一节中的样例代码:

```python
#!/usr/bin/python2

from collections import namedtuple
from ansible.parsing.dataloader import DataLoader
from ansible.vars import VariableManager
from ansible.inventory import Inventory
from ansible.playbook.play import Play
from ansible.executor.task_queue_manager import TaskQueueManager

Options = namedtuple('Options', ['connection','module_path', 'forks', 'remote_user', 'private_key_file', 'ssh_common_args', 'ssh_extra_args', 'sftp_extra_args', 'scp_extra_args', 'become', 'become_method', 'become_user', 'verbosity', 'check'])
# initialize needed objects
variable_manager = VariableManager()
loader = DataLoader()
options = Options(connection='local', module_path='/path/to/mymodules', forks=100, remote_user=None, private_key_file=None, ssh_common_args=None, ssh_extra_args=None, sftp_extra_args=None, scp_extra_args=None, become=None, become_method=None, become_user=None, verbosity=None, check=False)
passwords = dict(vault_pass='secret')

# create inventory and pass to var manager
inventory = Inventory(loader=loader, variable_manager=variable_manager, host_list='localhost')
variable_manager.set_inventory(inventory)

# create play with tasks
play_source =  dict(
        name = "Ansible Play",
        hosts = 'localhost',
        gather_facts = 'no',
        tasks = [ dict(action=dict(module='debug', args=dict(msg='Hello Galaxy!'))) ]
    )
play = Play().load(play_source, variable_manager=variable_manager, loader=loader)

# actually run it
tqm = None
try:
    tqm = TaskQueueManager(
              inventory=inventory,
              variable_manager=variable_manager,
              loader=loader,
              options=options,
              passwords=passwords,
              stdout_callback='default',
          )
    result = tqm.run(play)
finally:
    if tqm is not None:
        tqm.cleanup()
```

这段代码是直接可以执行的: 在一台已经安装好ansible的机器上, 将上面这段代码保存为ansible_test.py, 则可以按下面的方法来执行:

```
xiaket@xyw-admin03:~$ python ansible_test.py

PLAY [Ansible Play] ************************************************************

TASK [debug] *******************************************************************
ok: [localhost] => {
    "msg": "Hello Galaxy!"
}
```

上面的python代码中, 除掉import部分, 实际上可以分为三块内容. 第一块是对象的实例化(10-19行), 第二块是play的初始化(21-28行), 第三部分是用TaskQueueManager载入对应的实例, 运行任务(30-44行).

## import

我们先来看下import部分, namedtuple是标准库中的容器, 可以不论.

第一个import的是DataLoader. 根据文档, 它用来加载yaml或json内容. 我们可以看到, 在测试代码中, 这个类被不加参数地实例化了一次, 后面被多次(Inventory, Play, TQM)使用. 从具体代码逻辑看, 这儿因为没有加载任何数据, 因此后面多次使用时都只是实例化/初始化中需要这个空实例而已.

第二个import的是VariableManager, 这是用来处理ansible各个层级(Playbook/Group/Host等)中的变量. 和DataLoader一样, 上面的测试代码中没提供任何有意义的数据给这个管理器, 因此也只是一个空实例.

第三个import的是Inventory, 这是ansible中的机器库管理器. 这个类实例化的时候指明需要使用localhost. 因此我们上面允许测试代码时也没有进行任何ssh连接.

第四个import的是Play, 这是ansible的一个核心概念, 表示一个远程操作. 在我们的测试代码中, 这个操作的名字是Ansible Play, 对本机操作, 不收集fact, 这个操作只会执行一个任务, 即运行一个debug模块, 模块被提供了一个msg参数, 值为Hello Galaxy! 另外, play的初始化过程还提供了variable_manager和loader的空实例.

第五个import的是TaskQueueManager. 顾名思义, 这是ansible的任务队列管理器. 它在实例化的过程中接受了上面的所有的空实例, 执行了实例的run方法来运行指定的play, 最后用实例的cleanup方法来清理现场.

## 其他对象的实例化

我们写了一个简单的查看函数分析了所有这些已实例化的对象们的属性, 我们暂不关注内置属性和方法, 也不关注值为None的属性, 则执行实例化后:

| 实例               | 属性名                | 类型        | 值                                     |
|--------------------|-----------------------|-------------|----------------------------------------|
| `variable_manager` | `extra_vars`          | defaultdict | 空                                     |
| loader             | 无                    |             |                                        |
| options            | check                 | bool        | False                                  |
| options            | connection            | str         | local                                  |
| options            | forks                 | int         | 100                                    |
| options            | module_path           | str         | /path/to/mymodules                     |
| inventory          | groups                | dict        | `{'ungrouped': ungrouped, 'all': all}` |
| inventory          | `host_list`           | str         | localhost                              |
| play               | DEPRECATED_ATTRIBUTES | list        | 已废弃属性列表, 从略                   |
| play               | ROLE_CACHE            | dict        | 空                                     |
| play               | accelerate            | bool        | False                                  |
| play               | `accelerate_ipv6`     | bool        | False                                  |
| play               | `accelerate_port`     | int         | 5099                                   |
| play               | `any_errors_fatal`    | bool        | False                                  |
| play               | `gather_facts`        | str         | no                                     |
| play               | handlers              | list        | 空                                     |
| play               | hosts                 | list        | `['localhost']`                        |
| play               | name                  | str         | Ansible Play                           |
| play               | `post_tasks`          | list        | 空                                     |
| play               | `pre_tasks`           | list        | 空                                     |
| play               | roles                 | list        | 空                                     |
| play               | strategy              | str         | linear                                 |
| play               | tags                  | list        | 空                                     |
| play               | tasks                 | list        | [一个ansible.playbook.block.Block实例] |
| play               | untagged              | frozenset   | `frozenset(['untagged'])`              |
| play               | vars                  | dict        | 空                                     |
| play               | `vars_files`          | list        | 空                                     |
| play               | `vars_prompt`         | list        | 空                                     |
| tqm                | passwords             | dict        | `{'vault_pass': 'secret'}`             |

可见, `variable_manager`和loader里面完全没什么东西, 而options是一个标准的具名元组, 于是我们直接从inventory的初始化开始看. 去掉注释和不那么重要的内部缓存初始化后, Inventory的`__init__`代码如下:

```python
class Inventory(object):
    def __init__(self, loader, variable_manager, host_list=C.DEFAULT_HOST_LIST):
        self.host_list = host_list
        self._loader = loader
        self._variable_manager = variable_manager

        # the inventory object holds a list of groups
        self.groups = {}

        self.parse_inventory(host_list)
```

基本就是将loader和`variable_manager`存到实例属性中去, 然后用`parse_inventory`方法来解析`host_list`. 在看`parse_inventory`的代码之前, 我们插播一下ansible获取配置的方式. 上面初始化的时候使用了C这个变量, 实际上它来自:

```python
from ansible import constants as C
```

这个import. 这个模块中放全局变量们. 大部分属性都是通过一个叫`get_config`的函数加载的. 其逻辑是, 先看环境变量, 然后看本地配置文件, 如果都找不到对应的属性名或者任何过程中出异常, 则使用默认值. 拿到值后根据`get_config`中指定的值的类型做适当的类型转换. 例如, 对于`C.DEFAULT_MODULE_PATH`这个值, 它会先去环境变量中找`ANSIBLE_LIBRARY`这个值, 找不到则去默认的配置文件的default节中找library这个值, 如果仍找不到, 则使用默认值`None`. 由于历史原因, 我们刚才看到的`C.DEFAULT_HOST_HOST`这个值会更复杂一点儿, 它会先去环境变量中找`ANSIBLE_INVENTORY`这个值, 找不到则去默认的配置文件的default节中找inventory这个值, 如果仍找不到, 则去环境变量中找`ANSIBLE_HOSTS`, 然后去找配置文件中的hostfile字段, 如果到这儿仍没找到, 则使用默认值`'/etc/ansible/hosts'`.

在我们的测试代码中, `host_list`已经被指定为`'localhost'`了. 因此, 在`parse_inventory`中, 实际上我们的列表没有得到任何解析, 只是self被添加啦一个属性groups, 其值在上表中有列出. 而Group在初始化的阶段也没有做额外的逻辑, 只是将初始化的参数放进实例而已, 可以当成空字典看待. 因此, `parse_inventory`的具体逻辑我们现在先从略了. 因此, Inventory的实例化就到此为止.

## Play的实例化

我们接下来看Play. 这货的实例化阶段就复杂多了. 初始化后的属性也有一堆. 首先看这个类的定义, 这个类定义时继承了三个类:

```python
class Play(Base, Taggable, Become):
    def __init__(self):
        super(Play, self).__init__()

        self._included_path = None
        self.ROLE_CACHE = {}
```

其中, Become是权限控制相关的基类, 我们先可以不管. Taggable是控制任务tag属性的类, 这个功能的介绍可以参考[官方文档](http://docs.ansible.com/ansible/playbooks_tags.html). 我们现在也可以忽略. 先直接看Base这个基类.

```python
class Base:
    def __init__(self):
        # initialize the data loader and variable manager, which will be provided
        # later when the object is actually loaded
        self._loader = None
        self._variable_manager = None

        # every object gets a random uuid:
        self._uuid = uuid.uuid4()

        # and initialize the base attributes
        self._initialize_base_attributes()

        # and init vars, avoid using defaults in field declaration as it lives across plays
        self.vars = dict()
```

我们可以看到, 这段逻辑里除了设置一些空属性外, 做了两件事情: 一件是给自己添加了一个uuid, 另一件是调用`_initialize_base_attributes`方法, 真正去设置属性:

```python
    def _initialize_base_attributes(self):
        # each class knows attributes set upon it, see Task.py for example
        self._attributes = dict()

        for (name, value) in self._get_base_attributes().items():
            getter = partial(self._generic_g, name)
            setter = partial(self._generic_s, name)
            deleter = partial(self._generic_d, name)

            # Place the property into the class so that cls.name is the
            # property functions.
            setattr(Base, name, property(getter, setter, deleter))

            # Place the value into the instance so that the property can
            # process and hold that value/
            setattr(self, name, value.default)
```

看到这段代码, 自然必须先去理解`self._get_base_attributes`的逻辑. 为了方便理解, 我们将这段代码适当补全:

```python
from functools import partial
from inspect import getmembers

BASE_ATTRIBUTES = {}

class Base:

    # connection/transport
    _connection          = FieldAttribute(isa='string')
    _port                = FieldAttribute(isa='int')
    _remote_user         = FieldAttribute(isa='string')
    # more item omitted by xiaket.

    def _get_base_attributes(self):
        '''
        Returns the list of attributes for this class (or any subclass thereof).
        If the attribute name starts with an underscore, it is removed
        '''

        # check cache before retrieving attributes
        if self.__class__ in BASE_ATTRIBUTES:
            return BASE_ATTRIBUTES[self.__class__]

        # Cache init
        base_attributes = dict()
        for (name, value) in getmembers(self.__class__):
            if isinstance(value, Attribute):
                if name.startswith('_'):
                    name = name[1:]
                base_attributes[name] = value
        BASE_ATTRIBUTES[self.__class__] = base_attributes
        return base_attributes
```

即, 首先检查自己是不是在缓存里面, 如果在缓存里面, 直接返回. 然后建一个空字典`base_attributes`, 将符合条件的类变量及其对应的值全部放进这个字典. 对于上面这段精简过的代码, 循环完成后, `base_attributes`的内容会是:

```python
{
    'connection': FieldAttribute(isa='string'),
    'port': FieldAttribute(isa='int'),
    'remote_user': FieldAttribute(isa='string'),
}
```

另外需要注意的是, 我们现在面对的不是Base这个类的实例化, 而是Play这个类的实例化. 因此, Become和Taggable这两个基类中的属性也会出现在`_get_base_attrributes`的返回结果中. 现在, 我们可以回头去看`_initialize_base_attribute`中的逻辑了. 对于我们拿到的每个类属性, 都给Base这个类设置上属性, 并给实例设置这个属性. 具体给类设置属性的时候, 三个静态方法的代码为:

```python
    @staticmethod
    def _generic_g(prop_name, self):
        method = "_get_attr_%s" % prop_name
        if hasattr(self, method):
            return getattr(self, method)()

        value = self._attributes[prop_name]
        if value is None and hasattr(self, '_get_parent_attribute'):
            value = self._get_parent_attribute(prop_name)
        return value

    @staticmethod
    def _generic_s(prop_name, self, value):
        self._attributes[prop_name] = value

    @staticmethod
    def _generic_d(prop_name, self):
        del self._attributes[prop_name]
```

在Base中, 实际上没有定义任何`_get_attr_xxx`的类方法. 只有在Become/Block/Taggable/Task中有这个定义. 可以看出只有对于特殊的属性, 才需要在子类的定义中为这些属性添加这些方法. 另外, 为类和实例都设置这个属性也许是为了方便获取类里面内置的默认值(吐槽: 你直接加个下划线去拿, 或者统一给一个get方法, 在get方法里处理这个`_get_attr_xxx`的逻辑不就行了吗, 你这儿的set和del基本没做事啊). 不得不说, 为了给这些属性在适当的地方设上适当的值, ansible也是操碎了心.

到这个时候, Play这个类中定义的一些默认值已经被设置成类属性了. 例如我们前面表格中的accelerate和strategy等属性就是在这儿(`_initialize_base_attributes`中)设置的.

至此, 我们已经了解了Play的实例化过程, 我们接下来看具体的加载过程:

```python
play = Play().load(play_source, variable_manager=variable_manager, loader=loader)
```

load这个方法的逻辑很简单:

```python
    @staticmethod
    def load(data, variable_manager=None, loader=None):
        p = Play()
        return p.load_data(data, variable_manager=variable_manager, loader=loader)
```

因为在load这个方法里面Play又实例化了一次, 我们回头可以将加载的代码改成下面这样:

```python
play = Play.load(play_source, variable_manager=variable_manager, loader=loader)
```

这样可以省掉一个实例化的步骤(这实例化还是略有些麻烦的, 好吧我这是洁癖).

`load_data`这个方法是在Base中定义的(后面我们会在Block的初始化中再跑一次类似的逻辑):

```python
    def load_data(self, ds, variable_manager=None, loader=None):
        ''' walk the input datastructure and assign any values '''

        assert ds is not None

        # cache the datastructure internally
        setattr(self, '_ds', ds)

        # the variable manager class is used to manage and merge variables
        # down to a single dictionary for reference in templating, etc.
        self._variable_manager = variable_manager

        # the data loader class is used to parse data from strings and files
        if loader is not None:
            self._loader = loader
        else:
            self._loader = DataLoader()

        # call the preprocess_data() function to massage the data into
        # something we can more easily parse, and then call the validation
        # function on it to ensure there are no incorrect key values
        ds = self.preprocess_data(ds)
        self._validate_attributes(ds)

        # Walk all attributes in the class. We sort them based on their priority
        # so that certain fields can be loaded before others, if they are dependent.
        base_attributes = self._get_base_attributes()
        for name, attr in sorted(base_attributes.items(), key=operator.itemgetter(1)):
            # copy the value over unless a _load_field method is defined
            if name in ds:
                method = getattr(self, '_load_%s' % name, None)
                if method:
                    self._attributes[name] = method(name, ds[name])
                else:
                    self._attributes[name] = ds[name]

        # run early, non-critical validation
        self.validate()

        # return the constructed object
        return self
```

前20行没什么好玩的逻辑, 真正开始做事是从第22行开始的. 这儿, 按照类继承的逻辑, 首先被执行的是Play中定义的`preprocess_data`, 而它里面只是做了一些简单的旧变量名检查/清理后, 就调用了基类的同名方法:

```python
    def preprocess_data(self, ds):
        ''' infrequently used method to do some pre-processing of legacy terms '''

        for base_class in self.__class__.mro():
            method = getattr(self, "_preprocess_data_%s" % base_class.__name__.lower(), None)
            if method:
                return method(ds)
        return ds
```

这段是在说, 对于Play这个类, 按照MRO的顺序(Play-Base-Taggable-Become-object), 依次执行类里面定义的`_preprocess_data_xxx`方法, 这儿的xxx是基类名字的小写. 对于Play而言, 真正被执行的只有Become里面的`_preprocess_data_become`, 这个方法很长, 具体用途是分析sudo/提权之类的逻辑, 在我们的测试代码中不存在, 因此不进去详细看了. 我们接下来看`load_data`里面的`_validate_attributes`:

```python
    def _validate_attributes(self, ds):
        '''
        Ensures that there are no keys in the datastructure which do
        not map to attributes for this object.
        '''

        valid_attrs = frozenset(name for name in self._get_base_attributes())
        for key in ds:
            if key not in valid_attrs:
                raise AnsibleParserError("'%s' is not a valid attribute for a %s" % (key, self.__class__.__name__), obj=ds)
```

这是一个校验的逻辑, 检查加载的时候, 不应该有任何非官方的属性. 这是一个防止使用错误的措施.

`load_data`中后面27-35行一方面检查了变量的优先级, 另一方面是做了各个不同参数的加载处理(第31行). 我们提供的参数有`name`, `hosts`, `gather_facts`, `tasks`. 而在Play及其基类中有的`_load`方法只有`_load_hosts`, `_load_tasks`:

```python
    def _load_hosts(self, attr, ds):
        '''
        Loads the hosts from the given datastructure, which might be a list
        or a simple string. We also switch integers in this list back to strings,
        as the YAML parser will turn things that look like numbers into numbers.
        '''

        if isinstance(ds, (string_types, int)):
            ds = [ ds ]

        if not isinstance(ds, list):
            raise AnsibleParserError("'hosts' must be specified as a list or a single pattern", obj=ds)

        # YAML parsing of things that look like numbers may have
        # resulted in integers showing up in the list, so convert
        # them back to strings to prevent problems
        for idx,item in enumerate(ds):
            if isinstance(item, int):
                ds[idx] = "%s" % item

        return ds
```

看过`_load_hosts`可以发现它没做什么特别的事情(除了将`'localhost'`类型转换成`['localhost']`外). 我们接下来看处理task加载的`_load_task`:

```python
    def _load_tasks(self, attr, ds):
        '''
        Loads a list of blocks from a list which may be mixed tasks/blocks.
        Bare tasks outside of a block are given an implicit block.
        '''
        try:
            return load_list_of_blocks(ds=ds, play=self, variable_manager=self._variable_manager, loader=self._loader)
        except AssertionError:
            raise AnsibleParserError("A malformed block was encountered.", obj=self._ds)
```

可见它基本上就是对`load_list_of_blocks`的异常处理而已. 我们来看这个函数的逻辑, 它是在`ansible.playbook.helpers`中定义的:

```python
def load_list_of_blocks(ds, play, parent_block=None, role=None, task_include=None, use_handlers=False, variable_manager=None, loader=None):
    '''
    Given a list of mixed task/block data (parsed from YAML),
    return a list of Block() objects, where implicit blocks
    are created for each bare Task.
    '''
    # we import here to prevent a circular dependency with imports
    from ansible.playbook.block import Block

    assert isinstance(ds, (list, type(None)))

    block_list = []
    if ds:
        for block in ds:
            b = Block.load(
                block,
                play=play,
                parent_block=parent_block,
                role=role,
                task_include=task_include,
                use_handlers=use_handlers,
                variable_manager=variable_manager,
                loader=loader
            )
            # Implicit blocks are created by bare tasks listed in a play without
            # an explicit block statement. If we have two implicit blocks in a row,
            # squash them down to a single block to save processing time later.
            if b._implicit and len(block_list) > 0 and block_list[-1]._implicit:
                for t in b.block:
                    t._block = block_list[-1]
                block_list[-1].block.extend(b.block)
            else:
                block_list.append(b)

    return block_list
```

首先需要注意的是, 这儿传进来的ds实际上是我们的测试代码中的`[ dict(action=dict(module='debug', args=dict(msg='Hello Galaxy!'))) ]`. 因为在`load_data`的第33行, 我们已经对ds做了一次取属性操作. 顺便吐槽下ansible这段代码, ds这个名字是数据结构本身就很让人无语了, 你还这么乱用, 不嫌眼晕不?

实际上真正跑逻辑是在这儿的第15行, 对Block开始初始化. 具体来说是Block的静态方法`load`, 传给它的参数是:

| 变量名           | 变量类型            | 变量值                                                              |
|------------------|---------------------|---------------------------------------------------------------------|
| block            | 字典                | `{'action': {'module': 'debug', 'args': {'msg': 'Hello Galaxy!'}}}` |
| play             | Play实例            | 我们还没完全初始化好的Play实例                                      |
| variable_manager | VariableManager实例 | 空                                                                  |
| loader           | DataLoader实例      | 空                                                                  |

我们具体来看代码:

```python
    @staticmethod
    def load(data, play=None, parent_block=None, role=None, task_include=None, use_handlers=False, variable_manager=None, loader=None):
        implicit = not Block.is_block(data)
        b = Block(play=play, parent_block=parent_block, role=role, task_include=task_include, use_handlers=use_handlers, implicit=implicit)
        return b.load_data(data, variable_manager=variable_manager, loader=loader)
```

`Block.is_block`是一个检查工具, 这儿返回的值是False. 接下来是Block这个类的实例化工作. 这个类继承了`Base`, `Become`, `Conditional`和`Taggable`四个类, 初始化仍和之前一样. 而这儿跑的`load_data`我们在前面已经见过了. 此时, 运行的`preprocess_data`是在Block中被定义的:

```python
    def preprocess_data(self, ds):
        '''
        If a simple task is given, an implicit block for that single task
        is created, which goes in the main portion of the block
        '''

        if not Block.is_block(ds):
            if isinstance(ds, list):
                return super(Block, self).preprocess_data(dict(block=ds))
            else:
                return super(Block, self).preprocess_data(dict(block=[ds]))

        return super(Block, self).preprocess_data(ds)
```

这儿的data就是我们上面表格中的字典, 我们已经测试过, 它不是一个Block, 真正运行的是`return super(Block, self).preprocess_data(dict(block=[ds]))`. 即仍是按MRO的顺序, 依次运行基类中的`_preprocess_data_xxx`方法. 这儿, Block的基类中没有跑什么有意义的代码, 可以不用管了. 接下来是`load_data`中的`_validate_attributes`, 也没做什么事情(没被定义, 按Base里的基本逻辑跑的). 我们可以看变量加载了, 具体来说, 是在Block中被定义的`_load_block`:

```python
    def _load_block(self, attr, ds):
        try:
            return load_list_of_tasks(
                ds,
                play=self._play,
                block=self,
                role=self._role,
                task_include=self._task_include,
                variable_manager=self._variable_manager,
                loader=self._loader,
                use_handlers=self._use_handlers,
            )
        except AssertionError:
            raise AnsibleParserError("A malformed block was encountered.", obj=self._ds)
```

仍是对`load_list_of_tasks`的异常处理. 我们仍按之前的做法, 将传给这个函数的变量总结一下:

| 变量名           | 变量类型            | 变量值                                                                    |
|------------------|---------------------|---------------------------------------------------------------------------|
| ds               | 字典                | `[{'block': [{'action': {'module': 'debug', 'args': {'msg': 'xxx'}}]'}}]` |
| play             | Play实例            | 我们还没完全初始化好的Play实例                                            |
| block            | Block实例           | 还没完全初始化好的Block实例                                               |
| variable_manager | VariableManager实例 | 空                                                                        |
| loader           | DataLoader实例      | 空                                                                        |

`load_list_of_tasks`也是在helper中被定义的:

```python
def load_list_of_tasks(ds, play, block=None, role=None, task_include=None, use_handlers=False, variable_manager=None, loader=None):
    '''
    Given a list of task datastructures (parsed from YAML),
    return a list of Task() or TaskInclude() objects.
    '''

    # we import here to prevent a circular dependency with imports
    from ansible.playbook.block import Block
    from ansible.playbook.handler import Handler
    from ansible.playbook.task import Task

    assert isinstance(ds, list)

    task_list = []
    for task in ds:
        assert isinstance(task, dict)

        if 'block' in task:
            t = Block.load(
                task,
                play=play,
                parent_block=block,
                role=role,
                task_include=task_include,
                use_handlers=use_handlers,
                variable_manager=variable_manager,
                loader=loader,
            )
        else:
            if use_handlers:
                t = Handler.load(task, block=block, role=role, task_include=task_include, variable_manager=variable_manager, loader=loader)
            else:
                t = Task.load(task, block=block, role=role, task_include=task_include, variable_manager=variable_manager, loader=loader)

        task_list.append(t)

    return task_list
```

根据我们的数据, 我们可以去掉不少芜杂的空变量和判断, 将上面的代码简化如下:

```python
def load_list_of_tasks(ds, play, block, variable_manager, loader):
    return [
          Block.load(
            ds[0], play=play, parent_block=block, variable_manager=variable_manager, loader=loader,
        ),
    ]
```

得, 又回到Block.load. 这个前面有代码了. 和前面执行的主要区别是有了一个`parent_block`参数, 而且此时`is_block`是True了. 具体过程我们不细跟了, 我们一起来看下最后实现的效果吧. 首先我们显然有一个play实例, 这个实例有一个tasks属性, 这个属性是一个列表, 里面是所以需要被执行的block. 因为我们只有一个任务, 于是可以定义一个新变量:

```python
block = play.tasks[0]
```

此时, 这个block有个名为block的属性, 里面是任务列表(对, 数据类型是列表了, 不能顾名思义认为它是一个Block实例), 列表里面有一个Task实例. 我们赋给这个实例了一些属性, 例如action的值为debug, args为一个字典, 其值为`{'msg': 'Hello Galaxy!'}`.

至此, 我们已经基本了解了ansible的变量加载过程. 初始化好了一个Play实例, 现在可以准备用TQM来运行这个实例了. TaskQueueManager的初始化代码比较简单, 只是一些赋值操作. 到现在, 整个初始化的部分我们已经完成了, 我们来总结一下:

* 实例化了Play和Inventory这两个实例, 加载到了一个TaskQueueManager的实例中去.
* 为了兼容性的关系, 另外实例化了两个空实例, 一个是VariableManager, 一个是DataLoader.
* Inventory里面是这次执行的对象. 对于我们的测试程序, 它唯一重要的属性是host_list, 值为'localhost'.
* Play是一个ansible中的核心类. 里面包含某个任务的完整信息, 这个类后面会在执行过程中被用到.
* Block是比Play低一个层级的存在, Block可以嵌套包含子Block, Block中需要包含另一个Block或一群Task.
* Task是对单个操作的描述. 里面包含执行的操作的模块名和参数.
* 所有这些实例准备好后, 用一个叫TaskQueueManager的类来运行.

## 运行Play

整个Play的运行大概可以包括下面这几个阶段:

1. 在TaskQueueManager中准备运行的参数和任务, 分配若干个进程来做事.
2. 通过Strategy来调度任务, 其依据是任务的状态.
3. 在WorkerProcess/TaskExecutor来运行任务并处理结果.

我们下面一点一点来看这个过程.

### 任务准备

直接看TQM的run方法, 为了简化代码, 我们删除了在我们的测试代码中没有起任何作用的代码:

```python
    def run(self, play):
        new_play = play.copy()

        # Fork # of forks, # of hosts or serial, whichever is lowest
        contenders =  [self._options.forks, play.serial, len(self._inventory.get_hosts(new_play.hosts))]
        contenders =  [ v for v in contenders if v is not None and v > 0 ]
        self._initialize_processes(min(contenders))

        play_context = PlayContext(new_play, self._options, self.passwords, self._connection_lockfile.fileno())

        # load the specified strategy (or the default linear one)
        strategy = strategy_loader.get(new_play.strategy, self)
        # build the iterator
        iterator = PlayIterator(
            inventory=self._inventory,
            play=new_play,
            play_context=play_context,
            variable_manager=self._variable_manager,
            all_vars=all_vars,
        )

        # and run the play using the strategy and cleanup on way out
        play_return = strategy.run(iterator, play_context)
        self._cleanup_processes()
        return play_return
```

首先play将自己做了一份镜像出来, 免得自己本体被修改. 然后计算了一共要开几个连接/处理进程来处理这次请求. 接下来是在TQM的`_initialize_processes`里:

```python
    def _initialize_processes(self, num):
        self._workers = []

        for i in range(num):
            main_q = multiprocessing.Queue()
            rslt_q = multiprocessing.Queue()
            self._workers.append([None, main_q, rslt_q])

        self._result_prc = ResultProcess(self._final_q, self._workers)
        self._result_prc.start()
```

对于我们的测试程序, 显然只需要起一个进程, 因此, 这儿的`_workers`列表中只有一个成员. 另外, 这儿会起一个本地的ResultProcess进程来接受服务器返回的内容. ResultProcess是一个`multiprocessing.Process`的子类, 它的`__init__`没有赋值以外的逻辑. 因为我们在`_initialize_processes`中在实例化了`ResultProcess`后马上运行了这个实例的start方法, 实际上运行的是`ResultProcess`的run方法. 这个run方法的逻辑是在处理结果, 根据不同的结果决定是否做一些回调. 具体的逻辑我们不细看了.

我们回头看TQM的run方法. 在初始化结果进程后, ansible将play的相关东西打包成了一个PlayContext.(吐槽, 你包这么多层不累吗...), 这货的初始化里面也是各种赋值, 我们不细看了. 需要细看的是PlayIterator的实例化, 在这个过程中, ansible为每个host设置了一个状态, 方便后面根据各种需求来做执行控制, 根据我们简单的测试case, 这个实例化过程可以简化为:

```python
class PlayIterator:
    def __init__(self, inventory, play, play_context, variable_manager, all_vars, start_at_done=False):
        self._play = play

        self._blocks = []
        for block in self._play.compile():
            new_block = block.filter_tagged_tasks(play_context, all_vars)
            if new_block.has_tasks():
                self._blocks.append(new_block)

        self._host_states = {}
        for host in inventory.get_hosts(self._play.hosts):
             self._host_states[host.name] = HostState(blocks=self._blocks)
```

这儿`self._blocks`会是有四个block实例的列表, block实例的`filter_tagged_tasks`实际上没起任何作用, 真正将一个task变成四个task的是Play实例的compile方法:

```python
    def compile(self):
        '''
        Compiles and returns the task list for this play, compiled from the
        roles (which are themselves compiled recursively) and/or the list of
        tasks specified in the play.
        '''

        # create a block containing a single flush handlers meta
        # task, so we can be sure to run handlers at certain points
        # of the playbook execution
        flush_block = Block.load(
            data={'meta': 'flush_handlers'},
            play=self,
            variable_manager=self._variable_manager,
            loader=self._loader
        )

        block_list = []

        block_list.extend(self.pre_tasks)
        block_list.append(flush_block)
        block_list.extend(self._compile_roles())
        block_list.extend(self.tasks)
        block_list.append(flush_block)
        block_list.extend(self.post_tasks)
        block_list.append(flush_block)

        return block_list
```

由于我们没有`pre_tasks`/`role`/`post_tasks`这些东西, 所以我们正好得到四个block, 即一个flush, 一个debug, 和两个flush.

### 任务调度

回到PlayIterator的初始化里面来, 这儿的`_host_states`的值会是:

```
{'localhost': HOST STATE: block=0, task=0, rescue=0, always=0, role=None, run_state=0, fail_state=0, pending_setup=False, tasks child state? None, rescue child state? None, always child state? None}
```

实际上这是一个单键字典, 其值为一个HostState实例. 具体的各个值都在上面写清楚了, 都是默认值(我们的测试案例实在简单).

前面我们已经知道, 这儿`new_play`的strategy已经被赋予了一个默认值linear. `strategy_loader`的逻辑不必深究, 需要了解的是, `ansible.plugins.strategy.linear`这个策略类被加载并实例化了. 后面的第24行, 我们将调用这个策略实例的run方法来真正执行操作. linear中实际的策略类的名字是StrategyModule, 它的初始化定义在`ansible.plugins.strategy`中. 不过只有基本的赋值逻辑, 我们不细说了. 直接看linear中的run方法. 这个方法很长, 有近200行, 在加上在这个方法的结尾还要执行基类里的run方法, 又有小几十行. 我们先厘清代码, 只关注主干的逻辑.

```python
    def run(self, iterator, play_context):
        '''
        The linear strategy is simple - get the next task and queue
        it for all hosts, then wait for the queue to drain before
        moving on to the next task
        '''
        # iteratate over each task, while there is one left to run
        result     = True
        work_to_do = True
        while work_to_do and not self._tqm._terminated:
            try:
                # xiaket: run job here.
            except (IOError, EOFError) as e:
                display.debug("got IOError/EOFError in task loop: %s" % e)
                # most likely an abort, return failed
                return False

        # run the base class run() method, which executes the cleanup function
        # and runs any outstanding handlers which have been triggered

        return super(StrategyModule, self).run(iterator, play_context, result)
```

上面整个run方法的最外层逻辑. 这段还是挺清楚的, 写一个死循环, 只有当满足条件才跳出. 接下来我们看try-except里面的逻辑. 经过清理后, 这段逻辑为:

```python
    try:
        hosts_left = [host for host in self._inventory.get_hosts(iterator._play.hosts) if host.name not in self._tqm._unreachable_hosts]
        work_to_do = False
        host_results = []
        host_tasks = self._get_next_task_lockstep(hosts_left, iterator)

        results = []
        for (host, task) in host_tasks:
            if not task:
                continue
            if self._tqm._terminated:
                break
            work_to_do = True

            if task.action == 'meta':
                self._execute_meta(task, play_context, iterator)
            else:
                task_vars = self._variable_manager.get_vars(loader=self._loader, play=iterator._play, host=host, task=task)
                self.add_tqm_variables(task_vars, play=iterator._play)
                templar = Templar(loader=self._loader, variables=task_vars)

                self._blocked_hosts[host.get_name()] = True
                self._queue_task(host, task, task_vars, play_context)

            results += self._process_pending_results(iterator, one_pass=True)

        results += self._wait_on_pending_results(iterator)
        host_results.extend(results)
    except (IOError, EOFError) as e:
        return False
```

这儿的`hosts_left`仍应是单个localhost的列表, 然后调用了`_get_next_task_lockstep`方法. 我们刚才看到, 经过Play实例的compile方法, 我们的一个任务变成了一个有四个任务的组合任务, 其中只有一个是我们的debug, 三个都是执行`flush_handlers`的meta任务. 我们现在看看`_get_next_task_lockstep`方法是怎么具体调配这四个任务的, 经过清理后, 这个方法的代码为:

```python
class StrategyModule(StrategyBase):

    def _get_next_task_lockstep(self, hosts, iterator):
        # make noop_task as a placeholder, omitted by xiaket.

        host_tasks = {}
        for host in hosts:
            host_tasks[host.name] = iterator.get_next_task_for_host(host, peek=True)

        # more code omitted for the moment.
```

好吧, 继续跟进Iterator的`get_next_task_for_host`里面去看, 剪掉和我们无关的逻辑后, 这段代码为:

```python
    def get_next_task_for_host(self, host, peek=False):

        display.debug("getting the next task for host %s" % host.name)
        s = self.get_host_state(host)

        task = None
        if s.run_state == self.ITERATING_COMPLETE:
            display.debug("host %s is done iterating, returning" % host.name)
            return (None, None)
        elif s.run_state == self.ITERATING_SETUP:
            s.run_state = self.ITERATING_TASKS
            s.pending_setup = False

        (s, task) = self._get_next_task_from_state(s, peek=peek)

        self._host_states[host.name] = s
        return (s, task)
```

即, 主要逻辑是拿到当前状态后, 根据当前状态来用`_get_next_task_from_state`来拿到下一个状态和当前任务, 然后将机器状态设为下一个状态并返回. 具体这个方法要继续跟进去看, 我们去掉了rescue和always的逻辑:

```python
    def _get_next_task_from_state(self, state, peek):

        task = None

        # try and find the next task, given the current state.
        while True:
            # try to get the current block from the list of blocks, and
            # if we run past the end of the list we know we're done with
            # this block
            try:
                block = state._blocks[state.cur_block]
            except IndexError:
                state.run_state = self.ITERATING_COMPLETE
                return (state, None)

            if state.run_state == self.ITERATING_TASKS:
                # clear the pending setup flag, since we're past that and it didn't fail
                if state.pending_setup:
                    state.pending_setup = False

                if state.fail_state & self.FAILED_TASKS == self.FAILED_TASKS:
                    state.run_state = self.ITERATING_RESCUE
                elif state.cur_regular_task >= len(block.block):
                    state.run_state = self.ITERATING_ALWAYS
                else:
                    task = block.block[state.cur_regular_task]
                    # if the current task is actually a child block, we dive into it
                    if isinstance(task, Block) or state.tasks_child_state is not None:
                        if state.tasks_child_state is None:
                            state.tasks_child_state = HostState(blocks=[task])
                            state.tasks_child_state.run_state = self.ITERATING_TASKS
                            state.tasks_child_state.cur_role = state.cur_role
                        (state.tasks_child_state, task) = self._get_next_task_from_state(state.tasks_child_state, peek=peek)
                        if task is None:
                            # check to see if the child state was failed, if so we need to
                            # fail here too so we don't continue iterating tasks
                            if state.tasks_child_state.fail_state != self.FAILED_NONE:
                                state.fail_state |= self.FAILED_TASKS
                            state.tasks_child_state = None
                            state.cur_regular_task += 1
                            continue
                    else:
                        state.cur_regular_task += 1

            elif state.run_state == self.ITERATING_COMPLETE:
                return (state, None)

            # if something above set the task, break out of the loop now
            if task:
                break

        return (state, task)
```

第一次进循环的时候, `state.run_state`是`self.ITERATING_TASKS`, 后面会拿到task, 具体来说, 第一次拿到的是一个参数为`flush_handlers`的meta任务, 而此时`state.cur_regular_task`被自增了1. 在整个测试程序的运行过程中, 这段逻辑被运行了5次, 前四次依次拿到meta/debug/meta/meta这四个任务, 第五次运行的时候因为在上面这段代码的开头遇到了IndexError, 因此`state.run_state`被设置`成self.ITERATING_COMPLETE`, 递归结束.

理解了这段逻辑后, 我们可以更具体地理解linear中的run方法了, 方便起见, 我将这段上面已经出现过的代码重新贴在下面. 此时, 第5行的输出我们已经能够理解了, 它会依次给出上面提到的这四个任务. 对于meta任务, 它有一个`self._execute_meta`方法, 对于非meta任务, 它会准备好任务的变量和执行环境, 设置好适当的flag, 交给`self._queue_task`来去运行这个任务. 然后会在`self._process_pending_results`中去等待结果, 看要不要根据结果的不同来执行一些逻辑. 后面的`self._wait_on_pending_results`中会去等所有机器都执行完任务.

```python
    try:
        hosts_left = [host for host in self._inventory.get_hosts(iterator._play.hosts) if host.name not in self._tqm._unreachable_hosts]
        work_to_do = False
        host_results = []
        host_tasks = self._get_next_task_lockstep(hosts_left, iterator)

        results = []
        for (host, task) in host_tasks:
            if not task:
                continue
            if self._tqm._terminated:
                break
            work_to_do = True

            if task.action == 'meta':
                self._execute_meta(task, play_context, iterator)
            else:
                task_vars = self._variable_manager.get_vars(loader=self._loader, play=iterator._play, host=host, task=task)
                self.add_tqm_variables(task_vars, play=iterator._play)
                templar = Templar(loader=self._loader, variables=task_vars)

                self._blocked_hosts[host.get_name()] = True
                self._queue_task(host, task, task_vars, play_context)

            results += self._process_pending_results(iterator, one_pass=True)

        results += self._wait_on_pending_results(iterator)
        host_results.extend(results)
    except (IOError, EOFError) as e:
        return False
```

上面这段代码应该可以算是整个ansbile在任务调度部分的核心代码了. 在我们真正去看每个任务是如何执行的之前, 我们先看下`self._execute_meta`这个方法的逻辑:

```python
    def _execute_meta(self, task, play_context, iterator):
        # meta tasks store their args in the _raw_params field of args,
        # since they do not use k=v pairs, so get that
        meta_action = task.args.get('_raw_params')

        if meta_action == 'noop':
            # FIXME: issue a callback for the noop here?
            pass
        elif meta_action == 'flush_handlers':
            self.run_handlers(iterator, play_context)
        elif meta_action == 'refresh_inventory':
            self._inventory.refresh_inventory()
        #elif meta_action == 'reset_connection':
        #    connection_info.connection.close()
        else:
            raise AnsibleError("invalid meta action requested: %s" % meta_action, obj=task._ds)
```

看来就是根据不同的meta任务调用一些内部函数而已. 我们先看看我们执行的`flush_andlers`:

```python
    def run_handlers(self, iterator, play_context):
        '''
        Runs handlers on those hosts which have been notified.
        '''

        result = True

        for handler_block in iterator._play.handlers:
            # FIXME: handlers need to support the rescue/always portions of blocks too,
            #        but this may take some work in the iterator and gets tricky when
            #        we consider the ability of meta tasks to flush handlers
            for handler in handler_block.block:
                handler_vars = self._variable_manager.get_vars(loader=self._loader, play=iterator._play, task=handler)
                templar = Templar(loader=self._loader, variables=handler_vars)
                try:
                    # first we check with the full result of get_name(), which may
                    # include the role name (if the handler is from a role). If that
                    # is not found, we resort to the simple name field, which doesn't
                    # have anything extra added to it.
                    handler_name = templar.template(handler.name)
                    if handler_name not in self._notified_handlers:
                        handler_name = templar.template(handler.get_name())
                except (UndefinedError, AnsibleUndefinedVariable):
                    # We skip this handler due to the fact that it may be using
                    # a variable in the name that was conditionally included via
                    # set_fact or some other method, and we don't want to error
                    # out unnecessarily
                    continue

                if handler_name in self._notified_handlers and len(self._notified_handlers[handler_name]):
                    result = self._do_handler_run(handler, handler_name, iterator=iterator, play_context=play_context)
                    if not result:
                        break
        return result
```

这儿的`iterator._play.handlers`是一个空列表. 我们这儿不会执行任何东西. 在真正的ansible应用中, 这儿执行handler主要是用于在有任何变化的时候执行一些任务. 例如官方文档里一个更新apache的playbook, 只有当apache真正被升级时, 重启apache服务的handler才会被执行. 因此, handler会在每个block的结尾被运行. 更多关于handler的详细文档, 可以参考[这儿](http://docs.ansible.com/ansible/playbooks_intro.html#handlers-running-operations-on-change).

### 任务执行

我们接下来看一个任务是怎么被具体执行的. 即看下`self._queue_task`的逻辑. 这段代码被定义在linear这个策略的基类中:

```python
    def _queue_task(self, host, task, task_vars, play_context):
        ''' handles queueing the task up to be sent to a worker '''

        display.debug("entering _queue_task() for %s/%s" % (host, task))

        task_vars['hostvars'] = self._tqm.hostvars
        try:
            # create a dummy object with plugin loaders set as an easier
            # way to share them with the forked processes
            shared_loader_obj = SharedPluginLoaderObj()

            queued = False
            while True:
                (worker_prc, main_q, rslt_q) = self._workers[self._cur_worker]
                if worker_prc is None or not worker_prc.is_alive():
                    worker_prc = WorkerProcess(rslt_q, task_vars, host, task, play_context, self._loader, self._variable_manager, shared_loader_obj)
                    self._workers[self._cur_worker][0] = worker_prc
                    worker_prc.start()
                    queued = True
                self._cur_worker += 1
                if self._cur_worker >= len(self._workers):
                    self._cur_worker = 0
                    time.sleep(0.0001)
                if queued:
                    break

            del task_vars
            self._pending_results += 1
        except (EOFError, IOError, AssertionError) as e:
            # most likely an abort
            display.debug("got an error while queuing: %s" % e)
            return
        display.debug("exiting _queue_task() for %s/%s" % (host, task))

```

里面没什么具体的逻辑, 主要是将所有的参数都传递给了WorkerProcess, 由这个类来做具体的任务执行. 这儿只是做了工作进程的调度, 并处理了一下异常. 回头来看, 我们在TQM的`_initialize_processes`中已经初始化好了一个worker, 不过没有初始化具体的工作进程, 只是将输出的队列(`rslt_q`)准备好了. 我们的WorkerProcess仍是在这里实例化的. 顺便吐槽下, 这儿的`main_q`在现在的代码中实际上从没使用.

接下来, 我们先来看WorkerProcess的实例化代码:

```python
class WorkerProcess(multiprocessing.Process):
    '''
    The worker thread class, which uses TaskExecutor to run tasks
    read from a job queue and pushes results into a results queue
    for reading later.
    '''

    def __init__(self, rslt_q, task_vars, host, task, play_context, loader, variable_manager, shared_loader_obj):

        super(WorkerProcess, self).__init__()
        # takes a task queue manager as the sole param:
        self._rslt_q            = rslt_q
        self._task_vars         = task_vars
        self._host              = host
        self._task              = task
        self._play_context      = play_context
        self._loader            = loader
        self._variable_manager  = variable_manager
        self._shared_loader_obj = shared_loader_obj

        # dupe stdin, if we have one
        self._new_stdin = sys.stdin
        try:
            fileno = sys.stdin.fileno()
            if fileno is not None:
                try:
                    self._new_stdin = os.fdopen(os.dup(fileno))
                except OSError:
                    # couldn't dupe stdin, most likely because it's
                    # not a valid file descriptor, so we just rely on
                    # using the one that was passed in
                    pass
        except ValueError:
            # couldn't get stdin's fileno, so we just carry on
            pass
```

除了复制了stdin, 这儿没什么新逻辑, 我们接着来看这个类的run方法:

```python
    def run(self):
        '''
        Called when the process is started, and loops indefinitely
        until an error is encountered (typically an IOerror from the
        queue pipe being disconnected). During the loop, we attempt
        to pull tasks off the job queue and run them, pushing the result
        onto the results queue. We also remove the host from the blocked
        hosts list, to signify that they are ready for their next task.
        '''
        try:
            # execute the task and build a TaskResult from the result
            debug("running TaskExecutor() for %s/%s" % (self._host, self._task))
            executor_result = TaskExecutor(
                self._host,
                self._task,
                self._task_vars,
                self._play_context,
                self._new_stdin,
                self._loader,
                self._shared_loader_obj,
            ).run()

            debug("done running TaskExecutor() for %s/%s" % (self._host, self._task))
            self._host.vars = dict()
            self._host.groups = []
            task_result = TaskResult(self._host, self._task, executor_result)

            # put the result on the result queue
            debug("sending task result")
            self._rslt_q.put(task_result)
            debug("done sending task result")

        except AnsibleConnectionFailure:
            self._host.vars = dict()
            self._host.groups = []
            task_result = TaskResult(self._host, self._task, dict(unreachable=True))
            self._rslt_q.put(task_result, block=False)

        except Exception as e:
            if not isinstance(e, (IOError, EOFError, KeyboardInterrupt)) or isinstance(e, TemplateNotFound):
                try:
                    self._host.vars = dict()
                    self._host.groups = []
                    task_result = TaskResult(self._host, self._task, dict(failed=True, exception=traceback.format_exc(), stdout=''))
                    self._rslt_q.put(task_result, block=False)
                except:
                    debug("WORKER EXCEPTION: %s" % e)
                    debug("WORKER EXCEPTION: %s" % traceback.format_exc())

        debug("WORKER PROCESS EXITING")
```

苦命的是, 我们仍然没到这棵苹果树的树洞的底部, 得继续进TaskExecutor去看任务是怎么被执行的, 还要看TaskResult这个类是干嘛的(虽然从名字来看已经很清楚了). 这儿的run大部分是组织和异常处理的逻辑, 没有做很重的东西. 我们先看TaskExecutor吧. 这个类的实例化过程只是在变量赋值, 我们忽略. 直接看它的run方法:

```python
    def run(self):
        '''
        The main executor entrypoint, where we determine if the specified
        task requires looping and either runs the task with
        '''
        try:
            items = self._get_loop_items()
            if items is not None:
                if len(items) > 0:
                    item_results = self._run_loop(items)

                    # loop through the item results, and remember the changed/failed
                    # result flags based on any item there.
                    changed = False
                    failed  = False
                    for item in item_results:
                        if 'changed' in item and item['changed']:
                            changed = True
                        if 'failed' in item and item['failed']:
                            failed = True

                    # create the overall result item, and set the changed/failed
                    # flags there to reflect the overall result of the loop
                    res = dict(results=item_results)

                    if changed:
                        res['changed'] = True

                    if failed:
                        res['failed'] = True
                        res['msg'] = 'One or more items failed'
                    else:
                        res['msg'] = 'All items completed'
                else:
                    res = dict(changed=False, skipped=True, skipped_reason='No items in the list', results=[])
            else:
                res = self._execute()

            # make sure changed is set in the result, if it's not present
            if 'changed' not in res:
                res['changed'] = False

            def _clean_res(res):
                if isinstance(res, dict):
                    for k in res.keys():
                        res[k] = _clean_res(res[k])
                elif isinstance(res, list):
                    for idx,item in enumerate(res):
                        res[idx] = _clean_res(item)
                elif isinstance(res, UnsafeProxy):
                    return res._obj
                return res

            res = _clean_res(res)
            return res
        except AnsibleError as e:
            return dict(failed=True, msg=to_unicode(e, nonstring='simplerepr'))
        finally:
            try:
                self._connection.close()
            except AttributeError:
                pass
            except Exception as e:
                display.debug(u"error closing connection: %s" % to_unicode(e))
```

这段看来主要时结果处理的逻辑, 例如任务成功或失败时添加适当标记和纪录等, 另外也处理了异常. 第7句的方法中处理了playbook中的with语句, 我们先略过. 真正的任务执行是在第十句(或者第37句)的`_execute`里面. 这是一个200行的大方法, 我们简化了在我们的测试脚本中完全没涉及到的逻辑, 得到下面这近四十行的代码:

```python
    def _execute(self, variables=None):
        '''
        The primary workhorse of the executor system, this runs the task
        on the specified host (which may be the delegated_to host) and handles
        the retry/until and block rescue/always execution
        '''
        templar = Templar(loader=self._loader, shared_loader_obj=self._shared_loader_obj, variables=variables)

        # Now we do final validation on the task, which sets all fields to their final values.
        self._task.post_validate(templar=templar)

        # get the connection and the handler for this execution
        if not self._connection or not getattr(self._connection, 'connected', False):
            self._connection = self._get_connection(variables=variables, templar=templar)
            self._connection.set_host_overrides(host=self._host)

        self._handler = self._get_action_handler(connection=self._connection, templar=templar)

        retries = 1   # modified by xiaket
        vars_copy = variables.copy()

        result = None
        for attempt in range(retries):
            try:
                result = self._handler.run(task_vars=variables)
            except AnsibleConnectionFailure as e:
                return dict(unreachable=True, msg=to_unicode(e))

            # set the failed property if the result has a non-zero rc. This will be
            # overridden below if the failed_when property is set
            if result.get('rc', 0) != 0:
                result['failed'] = True

            if 'failed' not in result:
                break

        return result
```

即, 真正的执行阶段包括下面这些步骤:

1. 任务校验(第10行)
1. 获得连接和handler, 准备执行任务(第12-17行)
1. 执行任务(第25行)
1. 结果处理(第29-35行)

任务校验和结果处理的逻辑我们不细看了. 我们开始看第二点和第三点.

#### 获得连接

这段逻辑首先是在`TaskExecutor._get_connection`中, 移除和测试代码无关的逻辑后, 代码如下:

```python
    def _get_connection(self, variables, templar):
        '''
        Reads the connection property for the host, and returns the
        correct connection object from the list of connection plugins
        '''

        if not self._play_context.remote_addr:
            self._play_context.remote_addr = self._host.address

        conn_type = self._play_context.connection
        if conn_type == 'smart':
            conn_type = 'ssh'
            if sys.platform.startswith('darwin') and self._play_context.password:
                # due to a current bug in sshpass on OSX, which can trigger
                # a kernel panic even for non-privileged users, we revert to
                # paramiko on that OS when a SSH password is specified
                conn_type = "paramiko"
            else:
                # see if SSH can support ControlPersist if not use paramiko
                try:
                    cmd = subprocess.Popen(['ssh','-o','ControlPersist'], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                    (out, err) = cmd.communicate()
                    if "Bad configuration option" in err or "Usage:" in err:
                        conn_type = "paramiko"
                except OSError:
                    conn_type = "paramiko"

        connection = self._shared_loader_obj.connection_loader.get(conn_type, self._play_context, self._new_stdin)
        if not connection:
            raise AnsibleError("the connection plugin '%s' was not found" % conn_type)

        return connection
```

这儿我们从`self._play_context`中拿到的`conn_type`是`localhost`, 这来源于实例化后Option中的相关属性. 我们可以看到, 这个方法中默认使用了ssh, 只有当ssh由于种种原因不可用时, 才使用paramiko. 具体获得连接是在第28行. 这个`connection_loader`属性是在`ansible.plugins`中定义的. 具体作用是根据不同的类型加载不同的连接plugin.

ansible所有支持的连接plugin都在`ansible.plugins.connection`中. 按照规范, 每个文件中都实现了`exec_command`, `put_file`和`fetch_file`这三个方法, 这三个方法给上一层的执行层面提供了统一的API.

#### 获得handler

这儿的handler和前文中的通知handler不是一个东西, 是ansible运行的模块中的处理器. 在`_execute`那段代码中, 这个值的初始化是在第17行, 调用了`self._get_action_handler`方法:

```python
    def _get_action_handler(self, connection, templar):
        '''
        Returns the correct action plugin to handle the requestion task action
        '''

        if self._task.action in self._shared_loader_obj.action_loader:
            if self._task.async != 0:
                raise AnsibleError("async mode is not supported with the %s module" % self._task.action)
            handler_name = self._task.action
        elif self._task.async == 0:
            handler_name = 'normal'
        else:
            handler_name = 'async'

        handler = self._shared_loader_obj.action_loader.get(
            handler_name,
            task=self._task,
            connection=connection,
            play_context=self._play_context,
            loader=self._loader,
            templar=templar,
            shared_loader_obj=self._shared_loader_obj,
        )

        if not handler:
            raise AnsibleError("the handler '%s' was not found" % handler_name)

        return handler
```

这时, 我们一开始在测试脚本中传递给ansible的模块名`debug`终于在这儿又一次出现了. 这儿第6行中就触发执行了查找模块的逻辑, 结果找到了, 因此这儿单handler_name就是`debug`. 后面做了一个模块的初始化就返回了. 模块的初始化里面也没做什么特别的事情, 就不细说了.

#### 执行任务

具体执行任务是调用debug这个模块的run方法:

```python
class ActionModule(ActionBase):
    ''' Print statements during execution '''

    TRANSFERS_FILES = False
    VALID_ARGS = set(['msg', 'var'])

    def run(self, tmp=None, task_vars=None):
        if task_vars is None:
            task_vars = dict()

        for arg in self._task.args:
            if arg not in self.VALID_ARGS:
                return {"failed": True, "msg": "'%s' is not a valid option in debug" % arg}

        if 'msg' in self._task.args and 'var' in self._task.args:
            return {"failed": True, "msg": "'msg' and 'var' are incompatible options"}

        result = super(ActionModule, self).run(tmp, task_vars)

        if 'msg' in self._task.args:
            result['msg'] = self._task.args['msg']

        elif 'var' in self._task.args:
            try:
                results = self._templar.template(self._task.args['var'], convert_bare=True, fail_on_undefined=True)
                if results == self._task.args['var']:
                    raise AnsibleUndefinedVariable
            except AnsibleUndefinedVariable:
                results = "VARIABLE IS NOT DEFINED!"

            if type(self._task.args['var']) in (list, dict):
                # If var is a list or dict, use the type as key to display
                result[to_unicode(type(self._task.args['var']))] = results
            else:
                result[self._task.args['var']] = results
        else:
            result['msg'] = 'Hello world!'

        # force flag to make debug output module always verbose
        result['_ansible_verbose_always'] = True

        return result
```

这儿前面是校验, 第18行是拿到结果, 后面是结果处理. 基本逻辑也很简单. 第18行调用了基类的run方法, 如下:

```python
    @abstractmethod
    def run(self, tmp=None, task_vars=None):
        """ Action Plugins should implement this method to perform their
        tasks.  Everything else in this base class is a helper method for the
        action plugin to do that.

        :kwarg tmp: Temporary directory.  Sometimes an action plugin sets up
            a temporary directory and then calls another module.  This parameter
            allows us to reuse the same directory for both.
        :kwarg task_vars: The variables (host vars, group vars, config vars,
            etc) associated with this task.
        :returns: dictionary of results from the module

        Implementors of action modules may find the following variables especially useful:

        * Module parameters.  These are stored in self._task.args
        """
        # store the module invocation details into the results
        results =  {}
        if self._task.async == 0:
            results['invocation'] = dict(
                module_name = self._task.action,
                module_args = self._task.args,
            )
        return results
```

没做什么事情, 由于invocation这个属性在debug模块中也没处理, 于是可以认为返回了一个空字典. 至此, ansible的请求处理已经结束了, 结果处理我们之前的代码中多少有些涉及, 基本上是返回一个字典, 里面装着所有的信息, 不细讲了.

#### 拼命令

我们都知道, ansible是不需要agent的, 原理大概是所有的命令参数情景都被拼成一个ssh命令, 在远程直接执行. 前面我们看到在debug模块中完全没有涉及到这方面的内容. 那么这些命令是怎么构造出来的呢? 实际上, 这部分逻辑是由三个插件来完成的.

##### 连接插件

首先是连接插件. ansible所支持的连接插件的路径是`ansible.plugins.connection`. 例如, 我们正常执行命令使用的是系统ssh命令, 但如果使用的是paramiko这个ssh库, 这个命令肯定就不一样了. 又比如, ansible还支持使用Windows Remote Mangement协议来管理远程服务器, 这个时候执行命令是在HTTP/HTTPS上又包装了的一层WinRM. 命令自然也不一样. 我们这儿简单看下ssh这个连接插件的fetch_file方法:

```python
    def fetch_file(self, in_path, out_path):
        ''' fetch a file from remote to local '''

        super(Connection, self).fetch_file(in_path, out_path)

        display.vvv(u"FETCH {0} TO {1}".format(in_path, out_path), host=self.host)

        # scp and sftp require square brackets for IPv6 addresses, but
        # accept them for hostnames and IPv4 addresses too.
        host = '[%s]' % self.host

        if C.DEFAULT_SCP_IF_SSH:
            cmd = self._build_command('scp', u'{0}:{1}'.format(host, pipes.quote(in_path)), out_path)
            in_data = None
        else:
            cmd = self._build_command('sftp', host)
            in_data = u"get {0} {1}\n".format(pipes.quote(in_path), pipes.quote(out_path))

        in_data = to_bytes(in_data, nonstring='passthru')
        (returncode, stdout, stderr) = self._run(cmd, in_data)

        if returncode != 0:
            raise AnsibleError("failed to transfer file from {0}:\n{1}\n{2}".format(in_path, stdout, stderr))
```

第4行实际上基类的`fetch_file`里面没做事. 后面就是根据配置来选择使用scp/sftp, 将远程文件复制到本地. 又比如, 作为一个API,  ssh.py中需要提供`exec_command`方法. 实际上, 这个方法里面都是在处理异常, 调用了`_exec_command`里的逻辑, 而`_exec_command`又是对`_run`的简单包装, 真正的逻辑都是在`_run`(240行的大东西)里面.

##### shell插件

这个插件的存在也是有显著的目的. 因为处理完远程登录后, 各个机器上的shell是不一样的, csh和bash的语法就有很大的区别, 又比如windows下必须要使用powershell. 这一层shell插件主要就是在处理这种差异性. sh.py这个模块比较大, 里面是整个bash/sh类shell的逻辑. 而csh.py文件就小多了:

```python
class ShellModule(ShModule):

    # How to end lines in a python script one-liner
    _SHELL_EMBEDDED_PY_EOL = '\\\n'
    _SHELL_REDIRECT_ALLNULL = '>& /dev/null'
    _SHELL_SUB_LEFT = '"`'
    _SHELL_SUB_RIGHT = '`"'

    def env_prefix(self, **kwargs):
        return 'env %s' % super(ShellModule, self).env_prefix(**kwargs)
```

有了适当的逻辑隔离后, csh就是在sh的基础上, 修改了一些csh特异性的语法. 对应的, sh中的这些值为:

```python
class ShellModule(object):

    _SHELL_EMBEDDED_PY_EOL = '\n'
    _SHELL_REDIRECT_ALLNULL = '> /dev/null 2>&1'
    _SHELL_SUB_LEFT = '"$('
    _SHELL_SUB_RIGHT = ')"'
    # more common class vars omitted by xiaket.

    def env_prefix(self, **kwargs):
        '''Build command prefix with environment variables.'''
        env = dict(
            LANG        = C.DEFAULT_MODULE_LANG,
            LC_ALL      = C.DEFAULT_MODULE_LANG,
            LC_MESSAGES = C.DEFAULT_MODULE_LANG,
        )
        env.update(kwargs)
        return ' '.join(['%s=%s' % (k, pipes.quote(text_type(v))) for k,v in env.items()])
```

回头看下, 果然, powershell.py的文件大小和sh.py差不多. 这也是因为实际上要写的逻辑都有那么多. 像csh.py这种只需要通过继承来改变一些类变量就能搞定一切的模块肯定不会多.

##### action插件

我们之前实际上已经看过一个debug插件了. 不过那个插件没做什么事情. 为了对这部分逻辑更深入的了解一番, 我们细看一下`ansible.plugins.action.script`里的代码:

```python
class ActionModule(ActionBase):
    TRANSFERS_FILES = True

    def run(self, tmp=None, task_vars=None):
        ''' handler for file transfer operations '''
        if task_vars is None:
            task_vars = dict()

        result = super(ActionModule, self).run(tmp, task_vars)

        if self._play_context.check_mode:
            result['skipped'] = True
            result['msg'] = 'check mode not supported for this module'
            return result

        if not tmp:
            tmp = self._make_tmp_path()

        creates = self._task.args.get('creates')
        if creates:
            # do not run the command if the line contains creates=filename
            # and the filename already exists. This allows idempotence
            # of command executions.
            res = self._execute_module(module_name='stat', module_args=dict(path=creates), task_vars=task_vars, tmp=tmp, persist_files=True)
            stat = res.get('stat', None)
            if stat and stat.get('exists', False):
                return dict(skipped=True, msg=("skipped, since %s exists" % creates))

        removes = self._task.args.get('removes')
        if removes:
            # do not run the command if the line contains removes=filename
            # and the filename does not exist. This allows idempotence
            # of command executions.
            res = self._execute_module(module_name='stat', module_args=dict(path=removes), task_vars=task_vars, tmp=tmp, persist_files=True)
            stat = res.get('stat', None)
            if stat and not stat.get('exists', False):
                return dict(skipped=True, msg=("skipped, since %s does not exist" % removes))

        # the script name is the first item in the raw params, so we split it
        # out now so we know the file name we need to transfer to the remote,
        # and everything else is an argument to the script which we need later
        # to append to the remote command
        parts  = self._task.args.get('_raw_params', '').strip().split()
        source = parts[0]
        args   = ' '.join(parts[1:])

        if self._task._role is not None:
            source = self._loader.path_dwim_relative(self._task._role._role_path, 'files', source)
        else:
            source = self._loader.path_dwim_relative(self._loader.get_basedir(), 'files', source)

        # transfer the file to a remote tmp location
        tmp_src = self._connection._shell.join_path(tmp, os.path.basename(source))
        self._connection.put_file(source, tmp_src)

        sudoable = True
        # set file permissions, more permissive when the copy is done as a different user
        if self._play_context.become and self._play_context.become_user != 'root':
            chmod_mode = 'a+rx'
            sudoable = False
        else:
            chmod_mode = '+rx'
        self._remote_chmod(chmod_mode, tmp_src, sudoable=sudoable)

        # add preparation steps to one ssh roundtrip executing the script
        env_string = self._compute_environment_string()
        script_cmd = ' '.join([env_string, tmp_src, args])

        result.update(self._low_level_execute_command(cmd=script_cmd, sudoable=True))

        # clean up after
        if tmp and "tmp" in tmp and not C.DEFAULT_KEEP_REMOTE_FILES:
            self._remove_tmp_path(tmp)

        result['changed'] = True

        return result
```

这段代码虽然有些长, 但逻辑并不复杂. 第5-17行是在做准备工作; 第19-37行是处理脚本文件在本地已经存在的情形. 后面就是将远程路径拼出来后将文件传至远程服务器, 然后视情况加上可执行权限后执行.

至此, 我们已经大致了解了拼命令的大致机制: action插件负责处理宏观层面上的逻辑, connection插件负责处理连接级别的逻辑, 而shell插件处理微观级别的命令构造.

# 通过其他方式来运行

我们在前一个部分里看到的那个测试脚本是由官方文档提供的, 其目的是演示ansible的请求是如何具体被处理的. 但是, 我们平常运行ansible的方式不是这样的. 首先, 即使是进行测试, 我们也会将常见的配置写到配置文件中, 并会提供一个inventory文件. 执行类似下面的命令:

```
[xiaket@dirac ~]ansible local -m shell -a "echo 'ok'"
i.admin.i | SUCCESS | rc=0 >>
ok
```

其中, inventory文件内容类似:

```
[xiaket@dirac ~]cat hosts
[3157]
223.252.222.118

[local]
i.admin.i
```

配置文件可能类似:

```
[xiaket@dirac ~]cat .ansible.cfg
[defaults]
remote_port = 3220
host_key_checking = False
forks = 10
inventory = /Users/xiaket/ansible/hosts
log_path=/Users/xiaket/var/log/ansible.log
ssh_args = -o ControlMaster=auto -o ControlPersist=1800s -o UserKnownHostsFile=/dev/null -o ServerAliveInterval=6 -o ServerAliveCountMax=5
control_path = %(directory)s/%%h-%%r
pipelining=True
```

然后, 对于日常维护的情况, 我们通常都是编写好ansible的playbook, 然后通过运行playbook来对远程服务器进行管理的. 我们接下来就看看这样的两种情形中, ansible是怎么处理请求的.

## ansible命令

我们刚刚已经给出了通过ansible命令来运行ansible的样例. 我们来深入分析这一命令执行过程. 首先是从ansible命令开始, 经清理后, 其代码如下:

```python
if __name__ == '__main__':

    display = LastResort()
    cli = None
    me = os.path.basename(sys.argv[0])

    try:
        display = Display()
        display.debug("starting run")

        sub = None
        try:
            if me.find('-') != -1:
                target = me.split('-')
                if len(target) > 1:
                    sub = target[1]
                    myclass = "%sCLI" % sub.capitalize()
                    mycli = getattr(__import__("ansible.cli.%s" % sub, fromlist=[myclass]), myclass)
            elif me == 'ansible':
                from ansible.cli.adhoc import AdHocCLI as mycli
            else:
                raise AnsibleError("Unknown Ansible alias: %s" % me)
        except ImportError as e:
            if e.message.endswith(' %s' % sub):
                raise AnsibleError("Ansible sub-program not implemented: %s" % me)
            else:
                raise

        cli = mycli(sys.argv)
        cli.parse()
        sys.exit(cli.run())

    except AnsibleOptionsError as e:
        cli.parser.print_help()
        display.error(to_unicode(e), wrap_text=False)
        sys.exit(5)
    except AnsibleParserError as e:
        display.error(to_unicode(e), wrap_text=False)
        sys.exit(4)
    except AnsibleError as e:
        display.error(to_unicode(e), wrap_text=False)
        sys.exit(1)
    except KeyboardInterrupt:
        display.error("User interrupted execution")
        sys.exit(99)
    except Exception as e:
        have_cli_options = cli is not None and cli.options is not None
        display.error("Unexpected Exception: %s" % to_unicode(e), wrap_text=False)
        if not have_cli_options or have_cli_options and cli.options.verbosity > 2:
            display.display("the full traceback was:\n\n%s" % traceback.format_exc())
        else:
            display.display("to see the full traceback, use -vvv")
        sys.exit(250)
```

这儿基本上就是在处理异常了. 真正的逻辑实际上是拿到自己的名字, 匹配到适合的cli. 具体到我们的命令, 匹配到的是AdhocCLI, 因此, 上面这段50多行的逻辑可以简化为:

```python
import sys
from ansible.cli.adhoc import AdHocCLI as mycli

cli = mycli(sys.argv)
cli.parse()
sys.exit(cli.run())
```

事实上, 如果将上面这段代码存成ansible_test.py, 则我们可以用下面的方式来运行这个脚本, 并得到和之前一致的结果:

```
[xiaket@dirac ~]python ansible_test.py local -m shell -a "echo 'ok'"
i.admin.i | SUCCESS | rc=0 >>
ok
```

我们进AdHocCLI里面看, 它的实例化代码在其基类CLI的__init__里面, 除了赋值外没其他逻辑, 我们忽略, 后面的parse和run方法是我们关心的, 首先是parse:

```python
    def parse(self):
        ''' create an options parser for bin/ansible '''

        self.parser = CLI.base_parser(
            usage='%prog <host-pattern> [options]',
            runas_opts=True,
            inventory_opts=True,
            async_opts=True,
            output_opts=True,
            connect_opts=True,
            check_opts=True,
            runtask_opts=True,
            vault_opts=True,
            fork_opts=True,
            module_opts=True,
        )

        # options unique to ansible ad-hoc
        self.parser.add_option('-a', '--args', dest='module_args',
            help="module arguments", default=C.DEFAULT_MODULE_ARGS)
        self.parser.add_option('-m', '--module-name', dest='module_name',
            help="module name to execute (default=%s)" % C.DEFAULT_MODULE_NAME,
            default=C.DEFAULT_MODULE_NAME)

        self.options, self.args = self.parser.parse_args(self.args[1:])

        if len(self.args) != 1:
            raise AnsibleOptionsError("Missing target hosts")

        display.verbosity = self.options.verbosity
        self.validate_conflicts(runas_opts=True, vault_opts=True, fork_opts=True)

        return True
```

它里面有使用其基类CLI的base_parser方法. 里面实际上是构建了一个optparse的实例, 添加了各种默认的参数, 这儿在AdHocCLI里面又额外添加了一些AdHoc运行方式所特有的参数. 例如我们传入的-m, 就在这儿被纪录了. 我们可以开始看run方法了, 精简后, 这个run方法如下:

```python
    def run(self):
        ''' use Runner lib to do SSH things '''
        # only thing left should be host pattern
        pattern = self.args[0]

        loader = DataLoader()
        variable_manager = VariableManager()
        variable_manager.extra_vars = load_extra_vars(loader=loader, options=self.options)

        inventory = Inventory(loader=loader, variable_manager=variable_manager, host_list=self.options.inventory)
        variable_manager.set_inventory(inventory)

        hosts = inventory.list_hosts(pattern)

        # dynamically load any plugins from the playbook directory
        for name, obj in get_all_plugin_loaders():
            if obj.subdir:
                plugin_path = os.path.join('.', obj.subdir)
                if os.path.isdir(plugin_path):
                    obj.add_directory(plugin_path)

        play_ds = self._play_ds(pattern, self.options.seconds, self.options.poll_interval)
        play = Play().load(play_ds, variable_manager=variable_manager, loader=loader)

        # now create a task queue manager to execute the play
        self._tqm = None
        try:
            self._tqm = TaskQueueManager(
                    inventory=inventory,
                    variable_manager=variable_manager,
                    loader=loader,
                    options=self.options,
                    passwords=passwords,
                    stdout_callback=cb,
                    run_additional_callbacks=C.DEFAULT_LOAD_CALLBACK_PLUGINS,
                    run_tree=run_tree,
                )

            result = self._tqm.run(play)
        finally:
            if self._tqm:
                self._tqm.cleanup()

        return result
```

可以看到, 这儿和我们前面的测试代码极其相似. 实际上, 后面的代码运行一直很相似, 直到在TaskExecutor获得handler那一步中:

```python
    def _get_action_handler(self, connection, templar):
        '''
        Returns the correct action plugin to handle the requestion task action
        '''

        if self._task.action in self._shared_loader_obj.action_loader:
            if self._task.async != 0:
                raise AnsibleError("async mode is not supported with the %s module" % self._task.action)
            handler_name = self._task.action
        elif self._task.async == 0:
            handler_name = 'normal'
        else:
            handler_name = 'async'
```

之前我们运行的时候, `self._task.action`是debug, 是一个内置的action. 而这次我们运行的是`-m shell`, 运行一个shell命令, 因此, 这儿拿到的`handler_name`是`normal`. 于是, 后面运行这个handler的方式也不一样了, 实际上调用的是ansible.plugins.action.ActionBase的`_execute_module`方法. 精简后, 这段代码为:

```python
    def _execute_module(self, module_name=None, module_args=None, tmp=None, task_vars=None, persist_files=False, delete_remote_tmp=True):
        '''
        Transfer and run a module along with its arguments.
        '''
        if task_vars is None:
            task_vars = dict()

        # if a module name was not specified for this execution, use
        # the action from the task
        if module_name is None:
            module_name = self._task.action
        if module_args is None:
            module_args = self._task.args

        (module_style, shebang, module_data) = self._configure_module(module_name=module_name, module_args=module_args, task_vars=task_vars)

        # a remote tmp path may be necessary and not already created
        remote_module_path = None
        args_file_path = None
        if not tmp and self._late_needs_tmp_path(tmp, module_style):
            tmp = self._make_tmp_path()

        if tmp:
            remote_module_filename = self._connection._shell.get_remote_filename(module_name)
            remote_module_path = self._connection._shell.join_path(tmp, remote_module_filename)
            if module_style in ['old', 'non_native_want_json']:
                # we'll also need a temp file to hold our module arguments
                args_file_path = self._connection._shell.join_path(tmp, 'args')

        if remote_module_path or module_style != 'new':
            self._transfer_data(remote_module_path, module_data)
            if module_style == 'old':
                # we need to dump the module args to a k=v string in a file on
                # the remote system, which can be read and parsed by the module
                args_data = ""
                for k,v in iteritems(module_args):
                    args_data += '%s="%s" ' % (k, pipes.quote(text_type(v)))
                self._transfer_data(args_file_path, args_data)
            elif module_style == 'non_native_want_json':
                self._transfer_data(args_file_path, json.dumps(module_args))

        environment_string = self._compute_environment_string()

        cmd = ""
        in_data = None

        if self._connection.has_pipelining and self._play_context.pipelining and not C.DEFAULT_KEEP_REMOTE_FILES and module_style == 'new':
            in_data = module_data
        else:
            if remote_module_path:
                cmd = remote_module_path

        rm_tmp = None
        if tmp and "tmp" in tmp and not C.DEFAULT_KEEP_REMOTE_FILES and not persist_files and delete_remote_tmp:
            if not self._play_context.become or self._play_context.become_user == 'root':
                # not sudoing or sudoing to root, so can cleanup files in the same step
                rm_tmp = tmp

        cmd = self._connection._shell.build_module_command(environment_string, shebang, cmd, arg_path=args_file_path, rm_tmp=rm_tmp)
        cmd = cmd.strip()

        res = self._low_level_execute_command(cmd, sudoable=sudoable, in_data=in_data)

        if tmp and "tmp" in tmp and not C.DEFAULT_KEEP_REMOTE_FILES and not persist_files and delete_remote_tmp:
            if self._play_context.become and self._play_context.become_user != 'root':
                # not sudoing to root, so maybe can't delete files as that other user
                # have to clean up temp files as original user in a second step
                cmd2 = self._connection._shell.remove(tmp, recurse=True)
                self._low_level_execute_command(cmd2, sudoable=False)

        try:
            data = json.loads(self._filter_leading_non_json_lines(res.get('stdout', u'')))
        except ValueError:
            # not valid json, lets try to capture error
            data = dict(failed=True, parsed=False)
            if 'stderr' in res and res['stderr'].startswith(u'Traceback'):
                data['exception'] = res['stderr']
            else:
                data['msg'] = "MODULE FAILURE"
                data['module_stdout'] = res.get('stdout', u'')
                if 'stderr' in res:
                    data['module_stderr'] = res['stderr']

        # pre-split stdout into lines, if stdout is in the data and there
        # isn't already a stdout_lines value there
        if 'stdout' in data and 'stdout_lines' not in data:
            data['stdout_lines'] = data.get('stdout', u'').splitlines()

        return data
```

这段代码比较长, 分析后, 它分为如下这几段:

1. 1-15行, 主要是在准备变量, 另外执行第15行的这个方法后, 拼出了一个要被执行的文件.
1. 17-40行, 准备将这个被执行的文件写到远程目录下去.
1. 42-60行, 计算出命令来.
1. 62行, 执行远程命令.
1. 64-87行, 处理结果.

对于我们的样例而言, 第一步里面被拼出来的文件包含了下面这几个文件:

* ansible/modules/core/commands/command.py
* ansible/module_utils/basic.py
* ansible/module_utils/splitter.py

没特别细看逻辑, 不过估计这个动态生成的内容不会是一股脑将所有东西全传给对面, 而是根据需要来的. 另外, 一些我们传递给ansible的参数也被写进了这个文件:

```python
# some code here
ANSIBLE_VERSION = '2.0.1.0'

MODULE_ARGS = "<<INCLUDE_ANSIBLE_MODULE_ARGS>>"
MODULE_COMPLEX_ARGS = '{"_raw_params": "echo \'ok\'", "_uses_shell": true}'
# some more code here.
```

在第3步中, 计算出来的命令是:

```bash
LANG=en_US.UTF-8 LC_ALL=en_US.UTF-8 LC_MESSAGES=en_US.UTF-8 /usr/bin/python /home/xiaket/.ansible/tmp/ansible-tmp-1457595446.2-114935694221703/command; rm -rf "/home/xiaket/.ansible/tmp/ansible-tmp-1457595446.2-114935694221703/" > /dev/null 2>&1
```

嗯, 先按需生成一个文件, 然后传过去, 再ssh过去执行这个文件. ansible大概就这三句话.

至于ansible-playbook, 我们就不细看了. 主要的变化也就是在VariableManager和DataLoader那边. 核心逻辑我们都已经讨论过了.
