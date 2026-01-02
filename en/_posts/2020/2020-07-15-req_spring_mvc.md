---
category: spring_boot
excerpt: Request Annotations
keywords: spring_boot
lang: en
layout: post
title: A Summary of SpringMVC Request Annotations
---

## Preface

Spring MVC analyzes the signature of a handler method and binds HTTP request information to the corresponding parameters of that method. In a new project I recently took over, they put a lot of commonly used info into headers, so I ended up using the `@RequestHeader` annotation. It’s pretty ordinary and I don’t use it that often, but it suddenly occurred to me that I should summarize it.

Of course, Spring MVC is very flexible about controller method signatures—you can pretty much define them however you like and still get the parameters you need.

##  Main Content

The more commonly used ways to get parameters at work:

- @PathVariable

  ```
  This is a commonly used parameter in RESTful APIs. The value corresponds to the part inside {} in the endpoint URL, and it can be used to retrieve parameters from the URL.
  ```

- @RequestParam

  ```
  This used to be a pretty common annotation for receiving parameters from the frontend, mainly for handling content encoded with the default HTTP content-type.
  // By default, the parameters are of type application/x-www-form-urlencoded
  ```
- @RequestBody

  ```
  This is a more popular way to receive parameters nowadays, generally used to handle data that is not encoded as Content-Type: application/x-www-form-urlencoded.
  The most common one is JSON, of course.
  ```
- @RequestHeader

  ```
  This is the annotation I’ve been using a lot recently, because my company puts the user’s userid and userkey in the header as required fields for every request message,
  so I often use this annotation to receive them.
  ```
- @CookieValue

  ```
  This is used similarly to @RequestParam, except it retrieves values from cookies. It’s actually very convenient—much more elegant than pulling it out manually in code.
  ```
  
  For most of the annotations above, besides the `value`, there’s also a `required` field. It defaults to `true`, meaning an exception will be thrown if the client doesn’t provide it. In practice, we usually change it to `false` manually—of course, because we’d rather return a friendly error message from our code.