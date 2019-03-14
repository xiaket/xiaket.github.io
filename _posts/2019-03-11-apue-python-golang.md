---
title:  "Some APUE experiments in Python and golang"
date:   2019-03-11 19:29 +1100
description: Some experiments from the APUE book using Python and golang.
lang: en
---

I have been reading Advanced Programming in Unix Environment these days, and I enjoyed the exposure to system APIs. As an infrastructure engineer, I don't think I'll have lots of chance to use these APIs directly, but they will give me a better understanding of how UNIX works, and make me a better engineer. All the sample code in the book was written in C, and I had re-written some of these in either Python or golang, so as to gain some hands on experience with these APIs.

### Sparse File

When we open a file of size `n` in write mode and seek to a position `m` where `m > n`, we have created a file with hole in it, aka sparse file. The ability to create a sparse file relies on the filesystem, UFS and APFS on mac does not support this feature, so our experiments have to be done on a Linux host. This should be an easy one, our first implementation is in Python:

<pre class="code" data-lang="python"><code>
#!/usr/bin/env python3
import os
buffer1 = "abcdefghij"
buffer2 = "ABCDEFGHIJ"

with open('file.hole', 'w') as fobj:
    fobj.write(buffer1)
    print(f"current offset: {fobj.tell()}")
    fobj.seek(16384)
    fobj.write(buffer2)
    print(f"current offset: {fobj.tell()}")
</code></pre>

The output would look like:

<pre class="code" data-lang="bash"><code>
current offset: 10
current offset: 16394
</code></pre>

Running on a Linux machine, the result is:

<pre class="code" data-lang="bash"><code>
~ # ls -ls
total 32
     8 -rwxr-xr-x    1 root     root         16394 Mar  9 01:16 file.hole
    20 -rw-r--r--    1 root     root         16394 Mar  9 01:16 file.nohole
</code></pre>

in which the `file.nohole` was created by running `cat file.hole > file.nohole`. This is in accordance with the book. Running on my mac, this file is of size 16394 and the block usage is 1. If we open the file, we'll see lots of `^@`(null bytes) in the file. However, as `cat` will ignore all the null bytes, the output would look like:

<pre class="code" data-lang="bash"><code>
{~}cat file.hole
abcdefghijABCDEFGHIJ
</code></pre>

In the above code snippet, we have used high level APIs and haven't used file descriptor based APIs. In the case of golang, I had utilised the now locked down `syscall` module, so it's more APUE-ly:

<pre class="code" data-lang="go"><code>
package main

import (
        "fmt"
        "os"
        "syscall"
)

func main() {
        var mode uint32
        mode = 10644
        fd, _ := syscall.Open("file.hole", syscall.O_CREAT|syscall.O_WRONLY|syscall.O_TRUNC, mode)
        syscall.Write(fd, []byte("abcdefghij"))
        fmt.Println("file descriptor: ", fd)
        curOffset, _ := syscall.Seek(fd, 0, os.SEEK_CUR)
        fmt.Println("current offset: ", curOffset)
        syscall.Seek(fd, 16384, os.SEEK_SET)
        syscall.Write(fd, []byte("ABCDEFGHIJ"))
        curOffset, _ = syscall.Seek(fd, 0, os.SEEK_CUR)
        fmt.Println("current offset: ", curOffset)
}
</code></pre>

which will generate similar results as presented above. Please note that in the APUE book, the author had used `Creat` call to create the file. Since this API is not available in macOS, we have used `Open`. To see a list of all the available APIs for the platform, you can run `go doc syscall`.

### SUID and EUID

The `access` API is designed to test whether the effective user id is able to access some file, without opening it. This could come in handy in SUID programs where we cannot do the test using open, because most likely the file can be opened since we are running as root. This piece of code is written in golang, and it goes like:

<pre class="code" data-lang="go"><code>
package main

import (
        "fmt"
        "golang.org/x/sys/unix"
        "os"
        "syscall"
)

func main() {
        if len(os.Args) != 2 {
                fmt.Println("usage: suid [pathname]")
                os.Exit(255)
        }
        pathName := os.Args[1]
        fmt.Println("path: ", pathName)
        if syscall.Access(pathName, unix.R_OK) != nil {
                fmt.Println("access error for ", pathName)
        } else {
                fmt.Println("read access OK for ", pathName)
        }
        _, err := syscall.Open(pathName, syscall.O_RDONLY, 0)
        if err != nil {
                fmt.Println("open error for ", pathName)
        } else {
                fmt.Println("open for reading OK for ", pathName)
        }
}
</code></pre>


As was suggested by APUE, after compiling this code to a binary, we should first run this against the binary file itself, it should give out two OKs. Then we should run this against some file that normal user does not have access to(`/etc/sudoers` for example) and it should give out two errors. Finally, we should use `chown` to change the owner of this binary to root and run `chmod u+s` against this binary to turn on set-user-ID bit, after that, the output would look like:

<pre class="code" data-lang="bash"><code>
{~}./suid /etc/sudoers
path:  /etc/sudoers
access error for  /etc/sudoers
open for reading OK for  /etc/sudoers
</code></pre>

### FTW: File tree walk

This final section is devoted to a file tree walk that will tell me how many files are found on my mac and what are their filetypes. Since we have done the last experiment in go, we would rebalance the universe with an implementation in Python:

<pre class="code" data-lang="python"><code>
#!/usr/bin/env python3
import os
import stat
import sys

types = [
    "S_ISBLK",
    "S_ISCHR",
    "S_ISDIR",
    "S_ISFIFO",
    "S_ISLNK",
    "S_ISREG",
    "S_ISSOCK",
]

type_counter = {name: 0 for name in types}

def update_counter(pathname):
    try:
        mode = os.stat(pathname).st_mode
    except FileNotFoundError:
        type_counter["S_ISLNK"] += 1
        return
    for name in types:
        if getattr(stat, name)(mode):
            type_counter[name] += 1
            return
    else:
        raise RuntimeError(f"Unknown type for {pathname}.")

for root, dirs, files in os.walk(sys.argv[1]):
    type_counter["S_ISDIR"] += len(dirs)
    for file in files:
        pathname = os.path.join(root, file)
        update_counter(pathname)

print(type_counter)
</code></pre>

You'll have to run it as `sudo ./ftw.py` and you could be asked for confirmation on giving your terminal access to Contact/Photo etc. The result on my mac is:

File type | Count | Percentage
--------- | ----- | ----------
regular file | 982651 | 80.99%
directory | 227109 | 18.72%
symlink | 2948 | 0.24%
character special | 576 | 0.05%
block special | 8 | 0.00%
socket | 73 | 0.00%
FIFO | 3 | 0.00%

Wow, 1 million files on my mac, what a surprise. If I remember correctly, when I was running Slackware with lots of packages installed 7 years ago, the number of files is around 100k. How time flies!
