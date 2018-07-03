# Migrating to Python 3: A real world example


At one of our clients' site, we have an internal tool written in Python which is used to build infrastructures in AWS. With the Python 2's end of life approaching, we plan to upgrade our codebase so it would support Python 3 and Python 2 simultaneously, so as to minimize the impact on the business. Sadly, this internal tool depends on an external open source software called [stacker](https://github.com/cloudtools/stacker), which does not support Python 3 yet. Therefore, I undertook in the last month the job to add Python 3 support for this open source software.

## Preparations

First, I'm not unprepared for this, I've watched some of the good videos in PyCon 2018:

* [Jason Fried - Fighting the Good Fight: Python 3 in your organization](https://www.youtube.com/watch?v=H4SS9yVWJYA)
* [Trey Hunner - Python 2 to 3: How to Upgrade and What Features to Start Using](https://www.youtube.com/watch?v=klaGx9Q_SOA)

I would also add that the stacker codebase does include a lot of tests, both unit tests and functional tests, which had helped tremendously during my journey. If your codebase does not have these tests in place, the upgrade would be a lot harder to achieve, and the outcome would be harder to measure. In that case, I would suggest add more tests and try to achieve at least 80% plus coverage.

## The process


## The takeaways



