---
category: other
excerpt: Sharing what I think is the most important phase for a purely technical person
  (not talking about management or architecture)
keywords: other
lang: en
layout: post
title: The Most Important Stage in Building a Strong Foundation as a Purely Technical
  Developer
---

## Preface

I’ve been working for a while now, and I’ve gained things, had realizations, and changed too. I went from being a clueless newbie who just hoped I could independently finish business requirements, to once wanting to write code that’s fast, good, and satisfying, and now to racking my brain trying to get as close as possible to zero bugs & squeeze every last bit out of the physical machine—high-quality, high-performance code.

I want to share some of what I believe are the progression changes for a purely technical developer (putting management and architecture aside) (purely my personal understanding—happy to discuss and agree-to-disagree). And I also want to share how to build what I think is the most important stage.

## The stages of a purely technical developer (in my mind)

![image-20210410111507387](https://mypicgogo.oss-cn-hangzhou.aliyuncs.com/tuchuang20210410111507.png)

<center>Another reminder to avoid pointless arguing: this is just my subjective view</center>

### How to complete development

This is the most entry-level stage. **Completing development** means you’re still not familiar with the development process, you can’t develop independently, and you can only barely get things done with guidance from others.

Maybe you just started, maybe you even—like at my company—joined through campus recruiting and don’t have permission to view business code, so you have to do assessment training in a dedicated area upstairs. Maybe you’re still working under a mentor while you’re just getting exposed to the company codebase. At this time you’re confused: you might not know the company’s development process, you might be curious about a lot of unknowns in development, and you might desperately want to become someone who can deliver business requirements.

At this stage I don’t really have any advice. `Be humble` `be attentive` `spend time` `study hard`—most people can meet the team’s needs. If you can’t, it might mean you’re not suited for development......



## How to develop efficiently

This is actually the part I want to focus on. I think the most important stage is also this one. **Efficient development** means you write code fast: as long as you put in the time, you can solve problems, instead of constantly stopping to get stuck on details. It feels smooth and not painful.

Of course I’m not saying the other stages aren’t important. I just don’t think I’m suitable to share those parts. Efficient development is something I’ve seriously thought about, and I do have some things I personally find useful, so I spent time summarizing them.

On one hand, I hope to “persist” these takeaways so I can keep doing them—apply them in every team I’ve been in, every requirement I handle, and every line of code I write. On the other hand, I want to see if I can give everyone some ideas. If you find them useful, you can think about them yourself—no need to follow my steps rigidly.

### Have your own variable naming habits

This is mentioned in a lot of dev advice: for things you see frequently, you *must* pay attention. When I was a junior dev, I didn’t really care—every time I needed a name, I’d just make something up.

“Just making something up” has a lot of downsides. First, it wastes time. Even if you’re being casual, you still want it to match your business logic somewhat. Even if you want to name it irresponsibly, you still have to consider your coworkers’ side-eye, so you end up hesitating (honestly, you just don’t want them to look down on you 😂). Second, if you always make it up, your naming style becomes a mess. You’ll most likely forget what you named your methods and end up searching forever.

I wrote an article before about my own naming habits—hope it can give you some reference. [Click](https://www.someget.cn/other/2021/10/05/coding_name01.html)

### Have your own coding habits

Coding habits are *really* important. They determine whether you enjoy writing code, and whether your coworkers enjoy reading/writing code with you.

But this is a broad topic. Here are some habits I personally care about:

- **Code comments**: try to make code for machines to read, and comments for humans to read. A lot of times it’s not that people can’t understand the code. It’s that in the main business flow, I see you calling a weirdly named method, then I jump in and it’s a super long method—I just want to understand the main business logic. If you add a one-line comment like “this line handles xxx data”, you might save me a lot of time. Most importantly... it saves *your own* time, because you’ll forget... Stop! Don’t argue with me—I argued like this a few years ago too. Now I don’t dare. My face hurts.
- Avoid reinventing the wheel. This also means you need to get familiar with popular wheels—like frequently browsing Hutool’s source code. I often see coworkers implement set intersection/union themselves, with super long code that isn’t robust and throws exceptions all the time. But Hutool already has great implementations for intersection/union/difference. Another important point is communicating with coworkers: if someone already wrote a utility method that matches your need, just call it—slack++
- **Be good at summarizing commonly used code**. By “common code” I mean things like null checks. I often see `Objects.isNull` and `== null` mixed together. I’m not criticizing here. I think there are two reasons for writing like that: 1) you haven’t formed your own coding habits, 2) the code was copy-pasted.... Again, I’m not saying it’s wrong. I’m trying to explain the logic behind it. I want everyone to build their own coding habits—you can write however you want in your code. Some basics can be summarized, because once you keep writing, your style naturally becomes consistent, you develop your own habits, and you write faster and faster. I’ll list a few casually:
  - Null/empty checks for common objects and collections
  - Common collection needs, e.g., several ways to quickly create a list
  - Converting between JDK8 time and `Date`, and formatting
  - Common JDK8 Stream operators
  - A summary of commonly used JDK8 functional interfaces
- **Use tools well**. Life is short, I... use tools well. We’ve explored far too little of what IDEA can do. If you study it carefully, there are tons of features that can boost efficiency. And it’s not just IDEA—there are packet capture tools, API management tools, note management tools, encoding conversion tools, technical documentation lookup tools, middleware visualization clients, etc. Being in the tech industry, I often sigh: I’m really too lucky.

### Have a good habit of clarifying the business

Which is more important, business or technology? Everyone has their own answer. No matter what your answer is, everyone will definitely deal with requirements.

Our code is implemented based on requirements, and a big requirement can contain messy, complex business logic. How to understand these businesses quickly and well, and translate them into an implementation approach, is also a capability you need to improve at this stage. Sometimes you’re coding and suddenly realize you misunderstood something, and you have to throw it away and redo it. Sometimes you code and realize the business is too complex, and you didn’t fully understand it, so you picked the wrong technical solution. All of that is time cost—double the effort.

Here I can only share what I do. This also needs to be cultivated—it’s not something you “get” just by hearing it. Making the leap from intuitive thinking to rational thinking still requires a lot of practice. Decide the steps you need to do, follow them once, and after it becomes a habit, refine it. Here’s my method:

- If it’s a small requirement, after I’ve clarified it in the requirement walkthrough, I’ll directly write the wiki first. Every company is different; our internal wiki also serves as API documentation. I’ll replay the rough business logic in the wiki to confirm my understanding is correct, align interface parameters with upstream/downstream, and publish the doc directly. Then I start coding based on the wiki business flow: I first write pseudo-code as step-by-step comments. While writing comments, if a solution doesn’t fit, I can adjust in time. After finishing the comments, I implement under each comment—fast and effective.

- If it’s a more complex requirement, I’ll draw a flowchart first. Please don’t just look—try it yourself. It’s seriously *so so so* useful. Your understanding of the business goes up up. If you don’t do it, all the pits during development—whether communication or rollback—are blood-and-tears history.

  ![Self-study room billing rules](https://mypicgogo.oss-cn-hangzhou.aliyuncs.com/tuchuang20210410125820.png)

<center>Roughly draw something simple like this (Gaussian blur applied)</center>



### Have good delivery habits

The last two aren’t purely technical, but they’re closely related to tech. These are the kinds of things where you hear the “right principles” a lot, but still don’t do well. I used to be like that too. But to step out of your comfort zone, you still need to take initiative and change. Delivery is a broad concept. In my view, once you build good delivery habits, you’ll feel more comfortable writing code, your coworkers will be happier, and everyone will enjoy work more. Here are some of my usual habits:

- **Pay attention to upstream/downstream communication**. I write a lot of APIs, so upstream is whoever provides data, and downstream is whoever needs data from me. I rarely just throw a doc at someone or send a DingTalk message. Usually, if I can, I’ll walk over to their desk and talk. It’s more real-time, and it also makes the other person feel respected. For disputes, a lot of things are either “I change it” or “they change it”, so it’s about which side is more convenient. Explain things clearly—everyone is working and wants to do a good job, so you can definitely reach agreement. Also pay attention to follow-up: whether they provide an API to you and your testing is fine or not, it’s best to tell them so they have clarity. If you provide an API to others and they don’t respond for a long time, you should also ask.
- **Set your own DDL**. You should have your own time control for a project or requirement. Even if the quality management team doesn’t ask, you should have a ruler in your mind and strive to deliver on time. If the project team already set a deadline and you run into issues, you should report in time—don’t delay the whole release because of yourself.
- **Maintain your own checklist**. This is also very important. Keep records of your own DDL statements, newly added MQ topics, NoSQL keys, etc. Whether or not the team has an official record, anything you touched should be recorded by yourself. At critical moments, this can save you a huge amount of time.



## How to develop with high quality

This is what purely technical people keep pursuing. **High-quality development** means extremely high code quality while having low coupling with the business—tight logic while maximizing physical machine efficiency through reuse.

To be honest, this is also the direction I’m working toward. I don’t think I’m qualified to tell everyone how to achieve it yet—maybe there’s no upper bound forever. For example, I often read great coworkers’ code, read framework source code I like, look at excellent wheel code on GitHub, study the four 408 books, and try rewriting project code in multiple ways to compare differences. Every time I have a similar requirement implementation, but I see someone else doing it differently, I get curious and go research and compare, and ask the author what they were thinking. Sometimes you really gain a lot. A worse approach is reading others’ code with bias, thinking your own code is the best in the world. Emmm.... I’m also constantly trial-and-erroring, hoping my code quality can get higher and higher. I also really hope everyone can share how you do it—let’s just share different opinions.



## Afterword

I’m still growing. Maybe due to my knowledge scope, mindset level, and horizon, my current understanding might be biased. But isn’t growth exactly about constantly stepping out of bias and constantly correcting yourself? I hope that in a few years, when I write another summary, I’ll have different gains and different understandings. I also look forward to everyone sharing your own views.