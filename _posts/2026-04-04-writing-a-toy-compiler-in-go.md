---
title:  跟着AI学编译原理
date:   2026-04-04 07:07
ref:    writing-a-toy-compiler-in-go
---

有了AI之后, 学东西变得更容易了. 趁着复活节假期, 把之前接触过但是了解不深入的编译原理捡起来学习一下.

## LLVM IR

首先我读了网上找的两篇关于编译原理入门的文章, 一篇是[讲汇编的](https://mcyoung.xyz/2021/11/29/assembly-1/), 一篇是讲[LLVM IR的](https://mcyoung.xyz/2023/08/01/llvm-ir/). 我推荐读者自己去阅读一下这两篇, 内容都还挺不错(虽然对于这种内容, 怎么写也都算是re-hash而已). 如果不想读的话, LLVM IR是对于汇编的一层抽象, 是LLVM内部用来连接正常源代码和汇编之间的一个桥梁. 对于我这个toy project, 跟着LLVM IR就行了, 让实现一个编程语言变得特别简单(尤其是有AI帮忙).

## Design

我无意从头创建一个可以日常用的编程语言, 只是想探索一下这个过程中的技术栈而已, 所以我的提示词类似:

> 如果从头来设计一个编程语言, 要求有rust/c/go那样的性能, 而且适宜让AI agent来编写, 这个编程语言应该如何设计? 更进一步的, 如果只是想实现一个PoC, 需要做哪些工作呢?

其后, Claude给我了一些选项, 我按自己的喜好/直觉做了一些选择(或者说是瞎选). 再往后Claude就开始干活了. 我还让Claude做了一下性能的比较和优化, 最后结果是这个PoC的语言性能和Golang/C相当, 如果C代码没有认真优化(比如使用arena allocator), 那么这个PoC的性能甚至更好一些. 整个代码实现是用golang写的, runtime使用的是C. 在这个时代, 这已经属于技术细节了.

```
{🏠? ~/.xia/sha/git/reg/benchmark}time ./alloc3_regi

real	0m0.345s
user	0m0.284s
sys	0m0.032s
{🏠? ~/.xia/sha/git/reg/benchmark}time ./alloc3_c

real	0m1.091s
user	0m1.037s
sys	0m0.031s
{🏠? ~/.xia/sha/git/reg/benchmark}time ./alloc3_go

real	0m1.142s
user	0m1.914s
sys	0m0.091s
```

成品语法是这样的:

```
type Point struct {
    x: f64
    y: f64
}

fn distance(a: &Point, b: &Point) -> f64 {
    let dx = a.x - b.x
    let dy = a.y - b.y
    return sqrt(dx * dx + dy * dy)
}

fn midpoint(a: &Point, b: &Point) -> &Point {
    return new Point {
        x: (a.x + b.x) / 2.0,
        y: (a.y + b.y) / 2.0
    }
}

fn scale(p: &mut Point, factor: f64) {
    p.x = p.x * factor
    p.y = p.y * factor
}

fn main() {
    let p1 = new Point { x: 0.0, y: 0.0 }
    let p2 = new Point { x: 3.0, y: 4.0 }

    print(distance(p1, p2))  // 5.0

    let mid = midpoint(p1, p2)
    print(mid.x)  // 1.5
    print(mid.y)  // 2.0
}
```

编译和使用类似:

```
{🏠? ~/.xia/sha/git/regi-lang}./regic examples/point.regi
{🏠? ~/.xia/sha/git/regi-lang}./point
5
1.5
2
```

需要注意的是, 这个编程语言和其他很多语言最大的区别在于内存的管理. 这个PoC编程语言是根据变量作用域来管理内存的. 也就是说, 每个变量都有一个明确的作用域(region), 当这个作用域结束的时候, 变量占用的内存就会被自动回收掉. 这就避免了GC的开销, 同时也避免了手动管理内存的麻烦. 但是这也带来了一些限制, 比如不能有全局变量, 不能有闭包等等. 不过对于一个PoC来说, 这些限制是可以接受的.

## 代码流程分析

regic的main.go里面, 核心逻辑是这样的:

```go
p := parser.New(filename, string(src))   // 词法分析 + 语法分析 → AST
program := p.Parse()

typeChecker := checker.New()    //  类型推断和检查
typeChecker.Check(program)

regionChecker := checker.NewRegionChecker(typeChecker)
regionChecker.Check(program)    // 逃逸分析，确保引用不逃出 region

gen := codegen.New(typeChecker, targetTriple)
gen.Generate(program)
llvmIR := gen.Module().String() // AST → LLVM IR
cmd := exec.Command("clang", "-O2", "-Wno-override-module", "-o", *output, tmpFile.Name(), runtimePath, "-lm")  // 调用clang来编译.
```

下面分着来看看前三步的具体逻辑, 最后生成LLVM IR的步骤比较机械, 而调用clang来编译的这一步就更不用看了.

### 词法分析

词法分析的核心逻辑是这样的:

```go
func (p *Parser) Parse() *ast.Program {
    program := &ast.Program{}

    for !p.curIs(token.EOF) {
        decl := p.parseDecl()
        if decl != nil {
            program.Decls = append(program.Decls, decl)
        }
        p.nextToken()
    }

    return program
}
```

这儿的parseDecl会看当前的token是fn(函数)还是struct. 否则就直接报错, 这是因为在语言设计上, 我为了简化内存模型, 要求所有的变量都有一个明确的作用域(region):

```go
func (p *Parser) parseDecl() ast.Decl {
    switch p.cur.Type {
    case token.Fn:
        return p.parseFnDecl()
    case token.TypeKw:
        return p.parseTypeDecl()
    default:
        p.error(p.cur.Pos, fmt.Sprintf("expected declaration, got %s", p.cur.Type))
        return nil
    }
}
```

### 类型检查

类型检查的核心逻辑看了以后就觉得平平无奇了:

```go
func (c *Checker) Check(program *ast.Program) {
    // First pass: collect all type and function declarations
    for _, decl := range program.Decls {
        switch d := decl.(type) {
        case *ast.TypeDecl:
            c.collectTypeDecl(d)
        case *ast.FnDecl:
            c.collectFnDecl(d)
        }
    }

    // Second pass: check function bodies
    for _, decl := range program.Decls {
        if fn, ok := decl.(*ast.FnDecl); ok {
            c.checkFnDecl(fn)
        }
    }
}
```

就是把所有的Declaration(函数和struct定义)读到一个结构里面去, 然后挨个去检查函数的参数/返回值的类型是否正确:

```go
func (c *Checker) checkExpr(expr ast.Expr) types.Type {
    switch e := expr.(type) {
    case *ast.Ident:
        return c.checkIdent(e)
    case *ast.IntLit:
        return types.Typ_I64
    case *ast.BinaryExpr:
        return c.checkBinaryExpr(e)
    case *ast.CallExpr:
        return c.checkCallExpr(e)
    // ...
    default:
        return types.Typ_Invalid
    }
}
```

这儿, 有些能从ast拿到结果的就直接给了类型, 有些是到一个专门的函数里去做更细致的检查/推断, 比如, 我们在checkCallExpr里面, 先是对一些runtime层面实现的函数(print/sqrt)做类型检查, 然后再去检查用户提交的代码里定义的函数:

```go
func (c *Checker) checkCallExpr(expr *ast.CallExpr) types.Type {
    name := expr.Func.Name

    // Built-in functions
    switch name {
    case "print":
        for _, arg := range expr.Args {
            c.checkExpr(arg)
        }
        return types.Typ_Void
    case "sqrt":
        // sqrt(f64) returns f64
        if len(expr.Args) != 1 {
            c.errorf(expr.Pos(), "E0003", "sqrt expects 1 argument, got %d", len(expr.Args))
        } else {
        ╎   argType := c.checkExpr(expr.Args[0])
        ╎   if argType != types.Typ_F64 {
        ╎       c.errorf(expr.Args[0].Pos(), "E0003", "sqrt expects f64, got %s", argType)
        ╎   }
        }
        return types.Typ_F64
    // ...
    }

    fn := c.funcs[name]
    if fn == nil {
        c.errorf(expr.Pos(), "E0004", "undefined function: %s", name)
        return types.Typ_Invalid
    }

    if len(expr.Args) != len(fn.Params) {
        c.errorf(expr.Pos(), "E0003", "%s expects %d arguments, got %d", name, len(fn.Params), len(expr.Args))
        return types.Typ_Invalid
    }

    for i, arg := range expr.Args {
        argType := c.checkExpr(arg)
        paramType := fn.Params[i].Type

        if !c.assignable(paramType, argType) {
            c.errorf(arg.Pos(), "E0003", "cannot pass %s as %s", argType, paramType)
        }
    }

    if fn.Result == nil {
        return types.Typ_Void
    }
    return fn.Result
```

### 逃逸分析和region

这部分就不结合实现的代码来解释了, 因为不太具有代表性. 毕竟, 这个PoC的内存管理模式比较特殊. 结合实例解释一下这个PoC语言的特性吧:

```
fn main() {
    region {                    // depth 1
        let a = new Data {}     // a 属于 depth 1
        region {                // depth 2
            let b = new Data {} // b 属于 depth 2
            a = b               // 错误！depth 2 → depth 1
        }
    }
}
```

上面这段代码中, a和b的类型相同, 但是在depth 2中, 我们没有办法把depth 2的数据赋值给depth 1的变量. 因为这儿的深度就是生命周期, 深度越高的生命周期越短. depth 2的东西在depth 2结束的时候就被回收掉了, 所以没办法返回给depth 1. 对于这种场景, 我们要么通过一个函数来把数据返回出去, 要么把a和b的定义放到同一层. 在更深的depth/region里面, 我们仅仅是使用而不用返回.

## Learnings

在玩这个项目的过程中, 我也的确学到了编程语言里的各种特性都应该是在哪一层实现: 哪些东西是由runtime来提供的, 哪些东西是在CodeGen层面解决的, 而又有哪些是在库层面解决的. 比如, 在runtime层面, 我们会去:

* 做系统API调用, 例如随机数, 系统时间, 文件io, 网络io/socket, 进程线程, 信号处理等等.
* C-API调用比如类型转换等等.
* 自己在runtime这一层管理的逻辑, 比如基于region的内存管理的实现等等.

在CodeGen层面, 一个编程语言要实现:

* 控制流if/for等
* 运算符加减乘除等
* 结构体
* 函数调用
* 对于我们这个PoC的region, high level的region调度也是在语言/CodeGen层面实现的.

在库层面, 我们会需要提供一些函数供用户调用, 例如数学函数(sqrt/sin/cos等等), 字符串处理函数, 数据结构相关的函数(比如list/map/set等等), 以及一些系统调用的封装(比如文件io/网络io等等). 这些函数的实现可以是用C写的, 也可以是用我们这个编程语言写的. 往往, 我们需要将系统的API包装成更易于使用的函数. 不过对于我们这个PoC, 我们实际上没有实现这个特性.
