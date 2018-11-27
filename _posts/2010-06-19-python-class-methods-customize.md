---
title:  "自定义python类方法实现加减比较操作"
date:   2010-06-19 11:34 +0800
ref:    python-class-methods-customize
---

最近在写一个组内项目, 需要把一群一群的类似字典的对象实现类似相加的逻辑. 为了让代码更好看逻辑性更强, 偶玩了下python的自定义类方法.

首先更详细地介绍下背景: 我们需要在Django中记录一个模型变化的历史, 我们有需求会将这个模型的某个实例的现在的状态和它的若干个变化历史相加. 为此, 我们用Django的序列化方法把这个实例导出成一个json字符串, 然后用这个字符串实例化一个类似字典的类. 变化历史的各种相加相减操作就是通过自定义这个类似字典的类的特殊的类方法而实现的.

既然这个类是用一个json字符串来实例化的, 我们简单地将这个类的名字定为Json, 其初始化方法类似:

<pre class="code" data-lang="python"><code>
class Json(object):
    """
    This class is used to hold a model instance's information.
    """
    def __init__(self, _json_string):
        """
        This class is initialized with a json formatted string.

        The json formatted string is provided using django's serialization
        tool, which accept a QuerySet or a list as an object. So here we have
        to retrieve the first(and the only) object in the list.
        """
        self.init_string = _json_string
        _dictionary = json.loads(_json_string)[0]
        self.model = _dictionary['model']
        self.object_id = self.pk = _dictionary['pk']
        self.fields = _dictionary['fields']
</code></pre>

看起来很长一段代码, 实际上只是定义了若干基本类属性而已. 这些属性包括初始化字符串, 被序列化的实例的模型和主键, 以及一个存放原实例的属性的self.fields字典. 如果对这些名字不太熟悉可以自行去围观下django的序列化工具的json输出, [这个页面](http://docs.djangoproject.com/en/dev/topics/serialization/#topics-serialization)上有例子.

Json这个类只是存放了类的序列化的内容, 为了记录历史, 我们需要将两个这样的类相减以得出变化. 在定义相减这个操作之前, 我们需要定义一个用来存放历史变化的类:

<pre class="code" data-lang="python"><code>
class Jsondiff(object):
    """
    This object is used to save substraction results from two Json objects.
    """
    def __init__(self, _diffdict):
        """
        Input format specification
        --------------------

        the input json string represents a dictionary of differences. Like:
            {
                'fieldname': (newvalue, oldvalue),
            }
        It also contains a special field named '_model', containing the name of
        the model and the id of the object.
        A realworld example is provided below:
            {
                u'_object': (u'gsdb.server', 1),
                u'tag': (u'12535', u'12537'),
            }
        """
        self.fields = _diffdict
        self.model = self.fields['_object'][0]
        self.object_id = self.fields['_object'][1]
        del self.fields['_object']
</code></pre>

同样的, 看上去很长的代码只是干了很有限的几件事情: 从类初始化参数中拿到实例的模型和主键, 作为类属性保存起来, 并从初始化参数中删除这个用于存放元信息的特殊键值, 这样我们再后面进行各种操作时就不需要再讨论这个特殊的键值了.

OK, 两个类已经定义完了, 我们开始定义一些特殊的类方法. 首先, 我们需要定义一个方法能够比较两个Json实例的区别以得到一个Jsondiff实例. 我们需要实现下面的代码:

<pre class="code" data-lang="python"><code>
jsondiff0 = json1 - json2
</code></pre>

为此, 我们需要自定义Json的`__sub__`方法:

<pre class="code" data-lang="python"><code>
    def __sub__(self, _json):
        """
        This method would substract two Json objects and give a Jsondiff
        object.

        The object represented by _json is the old object, 'new - old' would
        make more sense than 'old - new'.
        """
        _diffdict = {
            '_object': (self.model, self.object_id),
        }
        for _field in self.fields:
            if self.fields[_field] != _json.fields[_field]:
                _diffdict[_field] = (self.fields[_field], _json.fields[_field])
        return Jsondiff(_diffdict)
</code></pre>

这段代码很容易理解. 你不是要比较两个Json对象吗? 既然所有相关的值都在self.fields里面, 那我们就一个个地进行比较, 如果有不同的地方就按照一个预设的格式记录下来. 我们这儿将这些记录放到一个字典里面, 处理完每个键后就直接将这个字典作为初始化Jsondiff类的参数实例化一个Jsondiff对象, 然后就可以直接返回这个对象了. 到这儿, 我们已经实现了前面写的json对象相减的代码. 下一步, 既然已经写了减法, 不写加法就不合理了:

<pre class="code" data-lang="python"><code>
# Since we can do:
jsondiff0 = json1 - json2
# we wanna have this, too:
json1 = json2 + jsondiff0
</code></pre>

好吧, 我们现在来定义加法:

<pre class="code" data-lang="python"><code>
    def __add__(self, _jsondiff):
        """
        This method would add a Json to a Jsondiff object.
        """
        _sum = copy.deepcopy(self)
        for _field in _jsondiff.fields:
            _new, _old = _jsondiff.fields[_field]
            if _sum.fields[_field] != _old:
                raise RuntimeError
            else:
                _sum.fields[_field] = _new
        return _sum
</code></pre>

此处, 为了避免执行加法后改变已有实例的属性, 我们用deepcopy将原来的Json对象复制了一份. 然后从Jsondiff里面读键值, 对于每个键值看看diff里的内容和当前的实例的属性有没有冲突, 以确定我们要进行的操作是不是合法的. 如果一切都没问题, 返回一个Json对象.

为了让这一切更和谐, 我们还定义了一个Jsondiff的__add__方法, 这样我们哪天把前后顺序弄反了也不会有多大的事情:

<pre class="code" data-lang="python"><code>
    def __add__(self, _json):
        """
        This method would add a Jsondiff to a Json object.
        """
        return _json + self
</code></pre>

有了这段代码, 我们在进行Json对象和Jsondiff对象的加法时可以肆无忌惮地将Jsondiff放在前面或者后面了. 而如果没有这个对象, 我们只能老老实实地将Jsondiff放在后面.

后来在使用中, 我发现我经常会需要比较两个Json对象的创建时间来比较哪个更新一点. 为了简化这些操作, 我给Json对象添加了一个date属性, 记录原模型的修改时间. 这样我每次只需要比较Json对象的date属性即可. 既然已经有了这个属性, 我们可以更进一步的定义`__cmp__`方法来使Json对象的比较更美观更和谐:


<pre class="code" data-lang="python"><code>
    def __cmp__(self, _json):
        """
        This method would compare two Json object's date.
        """
        return cmp(self.date, _json.date)
</code></pre>

定义了这个方法后, 我们能做类型下面的操作:

<pre class="code" data-lang="python"><code>
>>> json1 > json2
True
</code></pre>
