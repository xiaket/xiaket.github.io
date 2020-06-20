---
title:  Dynamic Buildkite pipeline in Python and Jinja2
date:   2020-06-20 20:12
lang:   en
ref:    dynamic-buildkite-pipeline-in-python-and-jinja2
---

A bit of a background first. As a cost management measure, we want to cleanup ephemeral Cloudformation stacks overnight in all the dev accounts that we have. We are using [Cloud Custodian](https://cloudcustodian.io) to write a maintainable policy and apply that policy at the end of day. As we have about a dozen dev accounts to apply this policy to, I wrote a script that will iterate over all accounts then over all allowed regions that we have, and run custodian to cleanup the stacks. As we are not using nested stacks, some of the low level stacks will not get removed because stack dependency, so we actually run the policy 4 times a day, and the schedule in buildkite looks like:

```
*/15 23 * * * Australia/Melbourne
```

This solution certainly had worked for us for quite some time, but it's growing old recently due to the following reasons:

1. We need to add more policies to the arsenal, and we don't need to run these new policies more than once a day.
2. Some of the policies has intricate dependencies, and it is better to run them in a ordered fashion.
3. We are throwing the new policies in, and as we have multiple regions and multiple accounts, the execution time of the pipeline is quickly exceeding 15 minutes.

To summarize, we need to do two things here:

1. Put policies into separate policy documents and run them with different schedules.
2. Run policies in parallel across all accounts.

The first requirement is relatively easy to do, but the second one would require us to write a dynamic pipeline as described [here](https://buildkite.com/docs/pipelines/defining-steps#dynamic-pipelines). I'm not a big fan of writing complex logic in bash, so I picked python to do the job. However, the issue with python is the virtual environment that you need to create and manage. In order to make this simple, I have a bash script to manage the venv and it will serve as the entrypoint of the pipeline:

```bash
#!/bin/bash

set -o errexit
set -o nounset
set -o pipefail

python3 -m venv venv
source venv/bin/activate
pip3 install -q --disable-pip-version-check jinja2 boto3 2>&1 > /dev/null

python3 scripts/render.py
```

This script is simple enough, all the juicy part lives in that `render.py`. Where we generate the pipeline using jinja2 template engine.

```python
#!/usr/bin/env python3
import os

import jinja2

# Pass in accounts and step
TEMPLATE = """
steps:
{% for account in accounts %}
  - label: ':{{ policy.icon }}: {{ policy.description }} in {{ account }}.'
    command: bash scripts/run-policy.sh {{ policy.action }}
    plugins:
      - ssh://git@scm.xxx.io:3999/bkpl/aws-assume-role-buildkite-plugin.git#v0.0.4:
          account: {{ account }}
          region: ap-southeast-2
{% endfor %}
"""

POLICIES = {
    "cfn": {
        "icon": "aws-cloudformation",
        "description": "Cleanup Cloudformation stacks",
        "action": "delete-ephemeral-cfn-stacks",
    },
    "snapshot": {
        "icon": "amazon-rds",
        "description": "Cleanup RDS auto snapshots.",
        "action": "delete-ephemeral-rds-snapshots",
    },
    "s3": {
        "icon": "amazon-s3",
        "description": "Cleanup ephemeral S3 buckets.",
        "action": "delete-ephemeral-s3-buckets",
    },
}

def main():
    if "BUILDKITE_MESSAGE" not in os.environ:
        raise RuntimeError("Please set `BUILDKITE_MESSAGE` to policy name.")
    policy = POLICIES[os.environ["BUILDKITE_MESSAGE"]]
    template = jinja2.Template(TEMPLATE)
    print(template.render(accounts=get_accounts(), policy=policy))

if __name__ == '__main__':
    main()
```

I have a few final notes here:

1. The output of the whole `pipeline.sh` should just be the pipeline, if you want to debug the template, you'll have to write to another file.
2. The `get_accounts` function was remove from the code snippet here, but we are getting all the account names from SSM in one of our management account.
3. Pick your buildkite emoji [here](https://github.com/buildkite/emojis)!
4. That `run-policy.sh` is just about iterating all aws regions and run the defined policy.
5. With this setup, we need to set the build message when you setup the buildkite schedule to be a policy name defined in `POLICIES`.
