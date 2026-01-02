---
category: java, tools
excerpt: Two Import Forms and `import static`
keywords: java, tools
lang: en
layout: post
title: A Summary of Java Imports
---

## Preface

When I was reading *Java 8 in Action*, I saw a lot of code handled like this:

![image-20210624200118873](https://mypicgogo.oss-cn-hangzhou.aliyuncs.com/tuchuang20210624200118.png)

<center>Call functions yourself at the two highlighted spots</center>

I was really curious. Later I found out that `import static` can import static members from a package, so you can reference them without the class name and use them directly in your code. Thinking about it, in real projects we often statically import constants from `constant` (for example, Redis key constants in a project)... turns out if your fundamentals aren’t solid, everything shakes... I’ve been using it all the time without even knowing, so I specifically wanted to summarize `import` and record it here.

## `lang` package — imported by default

Common types like `Long`, `String`, etc. are used so frequently that there’s a high chance you’ll use them in almost every class. The JDK puts them under the `java.lang` package—`lang` as in *language*. This package contains Java’s language fundamentals. So `java.lang` is imported by default, and you don’t need to import it yourself.

## Import styles

### Single-type import

Single-type import is easy to understand. Most of the time we import by type... and of course, most of the time the IDE imports for us. Most IDEs default to single-type imports: import whatever class you need.

```import java.util.List;``

### On-demand import

On-demand type import, like ``` import java.util.*```. The `*` is basically a wildcard, meaning you import based on the package rather than importing a single type. One thing to note: when people see the wildcard, they often assume it imports *all* classes under `java.util`. In reality, it doesn’t. The wildcard just tells the compiler where to search when resolving types. This has no impact on runtime performance; what it affects is compile time, because it takes longer to search. Next, I’ll explain how the compiler finds classes during compilation.

## How the compiler loads classes

The Java compiler locates the classes you need to import from the `bootstrap`, `extension`, and `system` paths. These are all top-level directories. The compiler determines an absolute path like this:

```html
Top-level directory → package name → class name (filename.class)
```

With a **single-type import**, since the package name and filename are known, the absolute path is determined directly, and it only needs to search once to find the class file.

With an **on-demand import**, it’s a bit more troublesome. Because the class name is not fixed, the compiler needs to do permutations and combinations and list all possible absolute paths.

For example, we need to use `List`, but we imported two wildcard packages:

```java
import java.util.*;
import java.sql.*;
public static void main(String[]args){
	List<Integer> list = Arrays.asList(1, 2, 3);   
}
```

Then the compiler will search for the `List` class in the following order:

1. First search the unnamed package (i.e., check whether there’s a `List` class in code without a declared `package`)
2. Then search the current package for a `List` class
3. Then check whether ```java.lang.List``` exists (this is imported by default, so it’s also checked)
4. Then check whether ```java.util.List``` exists
5. Note: even though it has already found it, the compiler will continue and check ```java.sql.List```

Basically it will stitch together absolute paths for all wildcard imports and try every possibility. If it finds two matches, the compiler will throw an error.

## Static import

Using ```import static``` instead of ``import`` enables static import. Both the single-type and on-demand forms above can be used with static import. Static import brings the static members of the imported class into the current class (because static members don’t require object instantiation; they’re initialized when the class is loaded and stored in the method area). Then in this class, you can call static methods directly by method name (as if the method were defined in this class), without needing `ClassName.staticMethodName`.

The **benefit** of doing this is that it can simplify some operations. For example, some constants are already long; add the class name, and if there’s a naming conflict you might even need to include the package name—one reference can turn into two lines of code. Static import is much more convenient and looks cleaner.

The **downside** is that static import can make code harder to read. Especially when importing methods: `ClassName.staticMethodName`—the class name and method name complement each other. A bare method name, when you’re not familiar with the codebase, makes it hard to infer meaning from the name alone. Also, if you statically import the same static method or static member variable from two different classes, it will cause an error—for example, wrapper classes all have `MAX_VALUE`.

## Afterword

You can see there’s actually a lot going on behind the imports that the IDE automatically handles for us—learning really is a long road. In practice, keeping your imports tidy is also very important. Because of changing requirements and team arrangements, I’ve seen company projects with over 200 lines of imports—terrifying to look at... and exhausting to deal with. I suggest that besides building good habits around 448 code formatting, you should also aim for good habits around optimizing imports.

![image-20210625162603484](https://mypicgogo.oss-cn-hangzhou.aliyuncs.com/tuchuang20210625162603.png)

<center>IntelliJ shortcut for optimizing imports</center>