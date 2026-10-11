---
category: linux
excerpt: 'Custom Linux Commands: Simplify Commands to Boost Efficiency'
keywords: linux, Mac, other
lang: en
layout: post
title: Some Uses of Configuration Files in the Linux Environment
---

## Introduction

Last time I introduced the different types of startup files and what they do. In this post, I want to share how I use those features to implement some functionality I need—basically a few practical use cases of my own. Note that everything in this article operates on ```~/.bash_profile```. Starting from macOS 10.15, the default shell has been changed to zsh, and shell startup no longer automatically loads and executes bash startup files. So please add the commands below to ```~/.zshrc```, or add ```source ~/.bash_profile``` to ```~/.zshrc```.

Same old routine: I’ll start with my pain points, then give my solutions. You can decide whether it’s useful for you before reading on.

My blog code is hosted on GitHub and runs on a Linux server. Every time I want to update content, ```I need to commit my local code to the remote, then log into the server and pull the code, then stop the online service, clean the blog cache, pull the code again, and finally restart the service```. It’s the same pile of steps every single time. As a programmer, the natural thought is to automate it with a script—these sequential commands are pretty simple. But after writing the script, I still had to cd into the script directory and run it with `./` every time. I’m lazy, so I wanted to turn that script into a command I could run from anywhere, just like ```ps```.

Then there’s another scenario. This one may not even need a script—it’s just that the command itself is ridiculously long. There’s no way I’m memorizing it, so every time I either have to copy-paste it or press ↑ to find it in history (and if I’ve typed a bunch of other commands in between, that gets annoying too. By the way, yes, you can use `history`, but the record length has a limit). For example, every time I start `spark-shell`, I need to specify a whole bunch of parameters and dependency paths... more than ten lines. No normal person is going to memorize that. Am I supposed to copy-paste it every time? That’s not very elegant.

So in this post, I’ll share how I solve these two annoyances: ```adding directories to the PATH environment variable``` and ```setting aliases for commands with alias```.

## Adding a PATH Environment Variable

Last time I talked about environment variables, especially the important one: PATH. To put it simply, every time you type a command in the terminal, the system goes through all the directories listed in PATH to see whether that command exists there. If it does, it runs it. If not, you get ```command not found```.

So if we want to turn our own script into a command, we need two steps. Let’s use a simple script ```echo “echo hello someget”``` as an example.

1. Create a script --- ```echo "echo hello someget" > my_script```

![image-20210601200144757](https://mypicgogo.oss-cn-hangzhou.aliyuncs.com/tuchuang20210601200144.png)

<center>Create the script file</center>



2. Give the script execute permission --- ```chmod a+x my_script``` where `a` means all users, `+` means grant permission, and `x` means execute permission

   ![image-20210601200242619](https://mypicgogo.oss-cn-hangzhou.aliyuncs.com/tuchuang20210601200242.png)

<center>You can see it turned green and now has execute permission</center>

3. Let’s try running `my_script` from the current project directory and then directly as a command `my_script`

![image-20210601200342695](https://mypicgogo.oss-cn-hangzhou.aliyuncs.com/tuchuang20210601200342.png)

<center>You can see the execute permission was set successfully, but it still can't be run outside the current directory</center>

4. Add the command to PATH so it can be used from anywhere. I highly recommend creating a `bin` directory under your home directory (the name can be anything, but by convention executable files are placed under `bin`), then add that `bin` directory to PATH. After that, any scripts you write can go there.

   1. Create `bin` --- ```mkdir ~/bin```

   ![image-20210601201342022](https://mypicgogo.oss-cn-hangzhou.aliyuncs.com/tuchuang20210601201342.png)

   2. Move our `my_script` into our own `bin` folder --- ```mv my_script ./bin```

   ![image-20210601203046457](https://mypicgogo.oss-cn-hangzhou.aliyuncs.com/tuchuang20210601203046.png)

   <center>Move it into your own `bin` folder</center>

   2. Modify PATH. Since I use bash on Linux, I recommend adding the path to PATH in `~/.bash_profile`. If you’re not sure what I’m talking about, you can check out my earlier posts: [Linux startup files](/linux/2021/02/15/linux_evnFile.html) and [Linux environment variables-----](/linux/2021/02/12/linux2_envVar.html) --- ```vim ~/.bash_profile```

   ![image-20210601202221960](https://mypicgogo.oss-cn-hangzhou.aliyuncs.com/tuchuang20210601202222.png)

   <center>Use colons to join paths</center>

   3. Use `source` to reload the file, or reopen the terminal window, then try running it again --- ```source ~/.bash_profile ```

   ![image-20210601203250790](https://mypicgogo.oss-cn-hangzhou.aliyuncs.com/tuchuang20210601203250.png)

   <center>Now it works even when you're not in that folder</center>

   **Finally**, from now on, any scripts can be placed under this `bin` directory. Once they’re there, you can use them globally just like normal commands.

   > Quick review
   >
   > 1. `export` is the command used to update environment variables and make them take effect. But once the shell is closed, they disappear, so you’d need to run `export` again every time. That’s why we write `export` into a startup file, so it gets executed whenever the shell starts.
   > 2. PATH uses colons for concatenation. If you define PATH twice, remember to use the ```$``` symbol to append the original PATH to the new one (because you can’t be sure whether other files also define PATH). So I strongly recommend simply appending to the existing PATH with ```:```. If you really want to redefine PATH, at least reference `$PATH` at the beginning.

   

   ## Using alias to Give Your Command a Nickname

   `alias` is a Linux mapping command that lets you map an existing command to another name. For example, the very common ```ll``` command is actually just a mapping for ```ls -lh```. Different distributions handle this differently. For example, the bash provided by Git on Windows doesn’t have the `ll` command. If you want a consistent workflow, you can add it manually—I’ll show how in a moment. First, let’s verify what I just said. If you simply type `alias` in the terminal, it will list all alias mappings. Then we can pipe it through a filter to find records containing ```ll```, and we’ll see that the last line is ```ll='ls -lh'```.

   ![image-20210602105544112](https://mypicgogo.oss-cn-hangzhou.aliyuncs.com/tuchuang20210602105544.png)

   <center>Use `alias` to list all mappings, then filter for entries containing `ll`</center>

   ![image-20210602105936260](https://mypicgogo.oss-cn-hangzhou.aliyuncs.com/tuchuang20210602105936.png)

   <center>Or use `which` to query the mapping relationship</center>

   Since alias mappings exist, handling very long commands becomes easy. Again, let’s use a simple command instead of the real-world requirement. We’ll map `hello` to ``` 'echo hello someget' ``` (note the difference from a script: the first one was a script, while this one is a direct command mapping).

   1. Since `alias` is very simple, we can directly run the command ```alias hello='echo hello someget'```

   ![image-20210602110455821](https://mypicgogo.oss-cn-hangzhou.aliyuncs.com/tuchuang20210602110455.png)

<center>You can see it already works normally</center>

2. But just like `export`, `alias` stops working once you close the shell window. So naturally, we think of writing it into a startup file.

   1. ```vim ~/.bash_profile  ```
   2. Add ```alias hello='echo hello someget'``` (note that there must be no spaces on either side of ```=```)

   ![image-20210602112337811](https://mypicgogo.oss-cn-hangzhou.aliyuncs.com/tuchuang20210602112337.png)

   3. Open a new terminal or run ```source ~/.bash_profile```

At this point, no matter how many times you open or close the shell, you can use `hello` to output `hello someget`. Using this method, you can also configure ```ll='ls -lh'```, or any other command you think is too long—like commonly used startup commands that you can never remember exactly and don’t feel like copy-pasting every time.

## Closing Thoughts

Startup files have many other very useful uses. Because they are automatically executed when the shell starts, they’re highly flexible and fun to play with. These are just some of my own use cases. If you also have some really helpful tricks, I’d love for you to share them with me.