---
title:  "Customizing Bash prompt in Golang"
date:   2018-05-17 19:56 09:51 +0800
lang:   en
---

I'm learning Go these days. I'm using it to [solve cryptopals problems](https://github.com/xiaket/cryptopals) and I begin to appreciate the language and start to think in Go. Apart from its wide use in the cloud sphere, Golang is perfect for daily commandline tools that need a balance between and maintainability and speed. I know Python could do similar things, but at least, once in a while, let's use Golang for a change. So in this article, I'll describe my recent adventure to customize my bash prompt, using Go.

In bash, it is really easy and fun to customize your prompt by setting up `PS1`. You could make it display, among many other things, your current username(`\u`), current time(`\t` and others), current working directory(`\w` and `\W`). You can find a full description of all available options in the bash manual. You could even throw in ascii control characters and make the prompt colorful. Here is a snippet that I've used in my bashrc a long time ago:

```bash
ORANGE=$(tput setaf 166)
RED=$(tput setaf 160)
BLUE=$(tput setaf 33)
CYAN=$(tput setaf 37)
RESET=$(tput sgr0)


# use ascii colors to show whether we are root.
if [ $UID -eq 0 ]
then
    export PS1="[\[${RED}\]\u@\[$CYAN\]\h \[$BLUE\]\w\[$RESET\]]"
else
    export PS1="[\[${ORANGE}\]\u\[$CYAN\]@\h \[$BLUE\]\w\[$RESET\]]"
fi
```

In general, this approach is great and it had served me for many good years. As time goes by, we need to evolve it, for example, git has become part of our daily workflow and it would be cool to display some git information if our current working directory is inside a git tree. Since this display of information is dynamical, we must find a way to execute a command and run the logic there. This is can be done by setting up `PROMPT_COMMAND`. As described in the manual: if set, the value is executed as a command prior to issuing each primary prompt. Actually, I've been using this bash feature all along to append bash history to the history file. So all I need to do is to expand the current solution and add some prompt specific logic here.

As we are moving to a dynamical prompt, we can do some more stuff in our prompt. One thing I'm not completely happy with my old prompt is that I frequently have to go into a python third party library to read its source code, and the current working directory could be rather lengthy, I want to have a short version of the directory display. So instead of displaying

```
/usr/local/lib/python2.7/site-packages/sympy/ntheory
```

I wish I could have something like:

```
/u/l/l/p/s/s/ntheory
```

We could do this with bash of course, but if you have worked with strings in bash, you will either uses the bash string manipulation feature, which is unreadable, or use external commands, which is more readable but slow. So I started writing a little script in Go that will read the current working directory and spit out my desirable path:

```go
func main() {
  dir, _ := os.Getwd()
  dir = strings.Replace(dir, os.Getenv("HOME"), "~", 1)
  paths := strings.Split(dir, "/")
  short_paths := make([]string, len(paths))
  for i, path := range paths {
    if (len(path) < 2) || (i == len(paths)-1) {
      short_paths[i] = path
    } else {
      if strings.HasPrefix(path, ".") {
        short_paths[i] = path[:3]
      } else {
        short_paths[i] = path[:2]
      }
    }
  }
  short_name := strings.Join(short_paths, "/")

  fmt.Println(short_name)
}
```

OK, from readablity and speed, I can pick two now. Let's get back to the git issue. There's a good implementation [here](https://github.com/mathiasbynens/dotfiles/blob/master/.bash_prompt). I copied that `prompt_git` function into my bashrc and made some twists to my prompt function, so it would look like this:

```bash
function prompt {
  if [ $? -eq 0 ]
  then
    col=${LIME}
  else
    col=${CRIMSON}
  fi
  history -a; history -n;
  PS1="${col}[${AQUA}"$(mypwd)
  gitst=$(prompt_git ${ORANGE} ${YELLOW})
  if [ -n "$gitst" ]
  then
    PS1+=" ${gitst}"
  fi
  if [ -n "${VIRTUAL_ENV}" ] && [[ "$PATH" == "${VIRTUAL_ENV}"* ]]
  then
    PS1="${ORANGE}^${RESET}${PS1}"
  fi
  PS1+="${col}]${RESET}"
}

export PROMPT_COMMAND='prompt'
```

That `mypwd` is a binary compiled from go code that we've seen earlier. It actually worked. The issue with this solution is it is fragmented and hard to understand. Exit status from last command, ascii color codes, brackets, commands, virtual environments flag, it's all messed up. To fix this is, of course, we need to migrate all these logic(including the git status function in bash) into that piece of Go code we've written, so it should behave like this:

```bash
function _xiaket_prompt {
  PS1="$(VAR1=VAL1 VAR2=VAL2 my_prompt $?)"
  history -a; history -n;
}
```

The idea is to pass in colors and brackets as environment variables for the prompt, and send the exit status of the last command as an argument.

The latest implementation of the gocode can be found [here](https://github.com/xiaket/etc/blob/master/go/my_prompt.go), and the bashrc file can be found [here](https://github.com/xiaket/etc/blob/6b30ebb8f9686cb5ae9739ec69f01d24986ccca4/bashrc#L51)  I end up adding one more feature in the code: some repetitive phrases in my git branch display will be replaced, so instead of displaying `feature/this_is_a_great_change`, we are showing `𝞿/this_is⁁nge`, I think it's a good balance between being concise and being informative.

However, please note some of the caveats here:

* I'm using a terminal emulator that supports 256 color, I hope that's not an issue.
* I've used some fancy characters for the flags, I hope with your font of choice, your terminal emulator would be able to display them correctly.
* I've used a very naive way (search for `.git` directory) to detect whether we are inside a git repo or a git tree, so it could be wrong.

Hope you'll find this useful.
