---
author: Rahul
authorLink: https://rahulvenugopal.github.io/haveyoumetrahul/
categories: ["Statistics"]
date: "2023-01-05T21:57:40+08:00"
description: 
draft: false
images: []
lightgallery: true
resources:
tags:
title: Linear mixed models
weight: 1
---

> You will get a glimpse of my learning route. There might be better resources to learn mixed models. Please email me if you have taken this road and hit me up with blogs/papers/books/courses/whatever which was super helpful and made the learning fun, easier and efficient

{{< figure src="mixed_models_verse.jpg">}}

1. Bodo winter's two tutorials to revise linear models
2. [Learning Statistical Models Through Simulation in R](https://psyteachr.github.io/stat-models-v1/introducing-linear-mixed-effects-models.html) chapter five is a good tutorial with a real word data. We will get to know the motivations to switch to mixed models
3. For the very first time we hear the terms `complete pooling`, `no pooling`, and `partial pooling`. If you are not very careful, you will miss `dummy coding`. Run and revise coding schemes from Andy Field's `DSUR` if this is not ringing any bell
4. [Tumble down the rabbit hole via this blog tutorial](https://www.tjmahr.com/plotting-partial-pooling-in-mixed-effects-models/). Having a working knowledge of R really pays off here. Get familiarised with the anatomy of `lme4` package
5. Oh, the good old `random factor` vs `fixed factor`. Only categorical factors would become `random factor`. There is this thumb rule that, the categorical variable should have minimum of `6` levels
6. `Random factors` can be thought of as `nestings` or `groupings` in the data. We are capturing the nature of the entire experiment
7. Get a feel of `shrinkage`. Tristan Mahr's blog (point no: 4) has a neat diagram which shows shrinkage. ![](https://www.tjmahr.com/figs/2017-06-22-plotting-partial-pooling-in-mixed-effects-models/shrinkage-plot-1.png)
> The average intercept and slope act like a center of gravity, pulling values parameter estimates towards it. Hmm, maybe gravity is not quite the right analogy, because the pull is greater for more extreme values. The lines near that center point are very short; they get adjusted very little. The lines in general get longer as we move away from the complete pooling estimate

> Douglas Bates (The wizard who wrote the THE book) says somewhere in his `lme4` package vignette that `shrinkage` is the process via estimates for individual subjects “borrow strength” from each other

8. Ahhh, the mandatory books links. Andrew Gelman and Jennifer presents Data Analysis Using Regression and Multilevel/Hierarchical Models. Statistical Rethinking: A Bayesian Course with Examples in R and Stan from Richard McElreath
9. If you never really bothered to figure out the incest between t test, regression, correlation etc. you would be lost amidst previous links. Don't worry. Here is a beacon of light, [from coding club's **Introduction to linear models**](https://ourcodingclub.github.io/tutorials/mixed-models/). Have fun with dinosaurs and their body lengths
10. Give yourself a break with [A fun intro to Multilevel Models in R](https://favstats.github.io/intro_multilevel/slides/#1)

### Want more to hit it off the roof?
1. [Mixed Models with R](https://m-clark.github.io/mixed-models-with-R/)
2. [PSYC 575 Multilevel Modeling (2022 Fall)](https://psyc575-2022fall.netlify.app/)
3. [An Introduction to Mixed Models for Experimental Psychology](http://singmann.org/download/publications/singmann_kellen-introduction-mixed-models.pdf)
4. [Statistical Modeling in R](https://singmann.github.io/mixed_model_workshop_2day/part1-statistical-modeling-in-r/statistical_modeling.html#1)
5. [Mixed Models in R](https://singmann.github.io/mixed_model_workshop_2day/part2-mixed-models-in-r/mixed_models.html#1)