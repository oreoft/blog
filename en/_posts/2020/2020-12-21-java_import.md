---
category: java
excerpt: Two Import Forms and `import static`
keywords: java, tools
lang: en
layout: post
title: Java `import` Summary
---

## Introduction

While reading *Java 8 in Action*, I came across many snippets like this:

![image-20210624200118873](https://mypicgogo.oss-cn-hangzhou.aliyuncs.com/tuchuang20210624200118.png)

<center>Two highlighted sections invoking functions directly</center>

I was quite curious at first, but later realized that `import static` allows you to import static members of a package or class. This way, you don't need to prefix them with the class name and can use them directly in your code. Thinking about it, constants in project constant classes (like Redis key constants) are indeed often statically imported... It really shows that without a solid foundation, things can easily get shaky. I had been using it all along without truly understanding it, so I decided to write a summary about `import` and document it here.

## The lang Package - Default Import

Common types such as `Long` and `String` are used so frequently that they are likely needed in almost every class. The JDK places them under the `java.lang` package—where `lang` stands for language, providing the core language fundamentals of Java. Therefore, the `lang` package is imported by default, meaning you never need to import it manually.

## Forms of Import

### Single-Type Import

Single-type import is quite straightforward. Most of our imports are done by specific type... Of course, in practice, our IDEs usually handle imports for us, and most IDEs default to single-type imports—importing only the specific class that is needed:

```java
import java.util.List;
```

### Type-Import-on-Demand (On-Demand Import)

Type-import-on-demand uses syntax like `import java.util.*`. The asterisk `*` acts as a wildcard, importing types based on package demand rather than individually. It is worth noting that when seeing the wildcard, people often mistakenly believe that all classes under `java.util` are immediately loaded into memory. In fact, this wildcard merely specifies the search directories when resolving types. It has zero impact on runtime execution speed; the only impact is on compilation speed because the compiler spends more time searching for classes. Let's look at how the compiler finds classes during compilation.

## How the Compiler Loads Classes

The Java compiler locates classes to import from the bootstrap, extension, and system paths. These directories are all top-level directories, and the compiler determines an absolute path using the following structure:

```html
Top-level directory → Package name → Class name (filename.class)
```

In **Single-Type Import**, because both the package name and file name are explicitly known, the absolute path is determined directly, requiring only a single search to locate the desired class file.

In **On-Demand Import**, things get slightly more involved. Because the class name is not specified upfront, the compiler needs to evaluate permutations and list all possible absolute paths.

For example, suppose we need to import the `List` class, but we use two on-demand wildcard imports:

```java
import java.util.*;
import java.sql.*;
public static void main(String[]args){
	List<Integer> list = Arrays.asList(1, 2, 3);   
}
```

The compiler will follow these steps to locate the `List` class:

1. Search the unnamed (default) package first to check if there is a `List` class without a package declaration.
2. Search the current package to check if a `List` class exists.
3. Check whether `java.lang.List` can be found (since `java.lang` is imported by default, it gets checked too).
4. Check whether `java.util.List` can be found.
5. Note: Even though it has already found one at this point, the compiler will still keep searching: `java.sql.List`.

Essentially, it will construct absolute paths for all wildcard imports and exhaust every possibility. If more than one matching class is found (e.g., both `java.util.List` and `java.sql.List`), the compiler will throw an ambiguous reference error.

## Static Import

Using `import static` instead of `import` enables static imports. Both single-type and on-demand imports can be used statically. A static import brings the static members of an imported class into the current class scope (since static members do not require instantiation, they are initialized when the class is loaded and stored in the method area / metaspace). You can then directly invoke static methods by their name within the class—just like a method declared directly inside the current class—without needing `ClassName.staticMethodName()`.

**Advantages:**
It can simplify code significantly. For example, some constant names are already quite long; adding the class name—or even the package name if there is a naming collision—can turn a single reference into two lines of code. Using static imports makes the code much cleaner and more concise.

**Disadvantages:**
Static imports can make code harder to read. When invoking methods, `ClassName.staticMethodName()` provides complementary context. A bare method name without context can be hard to understand unless you are already very familiar with the codebase. Furthermore, if you import two classes that share the same static method name or static variable (for example, wrapper classes that all have `MAX_VALUE`), it will cause a compilation error.

## Conclusion

As you can see, even everyday imports that the IDE automatically handles for us involve quite a lot of underlying details—proving that learning is a long and continuous journey. In daily development, keeping your imports organized is also crucial. Due to shifting requirements and personnel changes, I've seen project files in enterprise codebases with over two hundred lines of imports, which looks terrifying and is exhausting to scroll through. In addition to cultivating good code formatting habits, I suggest everyone also make a habit of optimizing their imports regularly.

![image-20210625162603484](https://mypicgogo.oss-cn-hangzhou.aliyuncs.com/tuchuang20210625162603.png)

<center>IntelliJ IDEA Optimize Imports Shortcut</center>