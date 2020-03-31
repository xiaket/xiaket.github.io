# Securing Buildkite

During a recent BAU mission, we set out to migrate our AWS/Buildkite to a new environment. This gave us a chance to look back to what we had done with our Buildkite setup in AWS, and we have improved/redone some of the setup so that the whole system is more secure and hopefully easier to use. This article describes our practices and hope you can find some of the patterns in this article helpful.

## Our AWS account setup

Before we jump onto the buildkite ship, we'll talk about our AWS account setup first, because that serves as a background for all our setups. We are using okta as our SSO/MFA provider. When we login to AWS via okta, we are logging into a special identity account, from that account, we then assume a role in our destination account. In AWS land, we have several workload accounts and non-workload accounts. The former is the usual dev/staging/prod AWS accounts and the latter includes tools/dns/audit and etc. In this non-wordload/workload split scheme, we have fully separated our runtime environment from the build environment.

![okta-identity-destination](/media/2020/okta-identity-destination.png)

As shown in the diagram above, we have identified several roles in the team. Typically, SRE people have access to the `AdminRole` and the `PowerUserRole` in identity account(via okta), while senior developers and developers have access to the `PowerUserRole` and `DeveloperRole` respectively. So when a senior developer logged in to okta and started the AWS application, he can only pick the `PowerUserRole` in the assume role window, while when an SRE logged in, he/she will pick from either `AdminRole` or `PowerUserRole`. Once we landed in the identity account, the only permission we have and the action we can do is to assume another role in the destination account(either workload or non-workload account). Someone with a `PowerUserRole` will be able to assume the `PowerUser` role in the workload account, and `DeveloperRole` in identity account will give someone `PowerUser` access in nonprod account and `ReadOnly` access in all the other workload accounts. Only the `AdminRole` can assume a role in non-workload accounts.

## Old Buildkite setup

As of today, we have several buildkite agent stacks built from the [elastic-ci-stack-for-aws](https://github.com/buildkite/elastic-ci-stack-for-aws) repo running in our tools account. The buildkite agent will use a `DeployRole` in each destination account to allow Buildkite agent to carry out missions in these accounts. We have a very loose control over who can assume that `DeployRole`, namely anyone in the tools account. We are using the team feature in buildkite but mostly for grouping purposes, not for security control. Also, we don't have a separate CDE(Card Data Environment) buildkite agent, which might give us compliance issues if we continue this practice. We are using the standard S3 secret bucket to manage the deploy keys and global secrets(hence this [hook](https://github.com/buildkite/elastic-ci-stack-s3-secrets-hooks)), which also lives in tools account. Furthermore, we have a bunch of buildkite plugins living in our internal repo, each will require a different deploy key to function properly.

The problem with this setup is it is relatively hard for non-SRE people to setup a pipeline on their own. They simply do not have the permission to write things into that S3 bucket. Moreover, we are using the same deploy key for multiple projects/repos and this is definitely not good. We do have a pipeline that will generate an SSH keypair and put the private key into a certain directory in that S3 secret bucket for us, but this only solves half of the problem. As although the user can setup the repo to use the public key generated in the process, this new key cannot checkout the internal buildkite plugins that we had developed.

## New Buildkite wishlist

Here's a wishlist of what we want from our new Buildkite setup:

* We have three separate agents stack, one for non-cde environment, `default`, one for cde environment, `cde`, and one for infra related pipelines, `infra`. The `default` agent do not have access to the cde/infra accounts.
* We store all the git deploy keys and enviroment variables in parameter store.
* We have a pipeline that will take a repo path (the namespace/project name pair, `torvalds/linux` for example) as input and create an SSH keypair, the private key is saved into parameter store, and the public part is added to Bitbucket.
* We do not store any secrets in that S3 bucket.
* We have all the buildkite plugins in the same project, and we have assigned a project level deploy key to it. The private key is loaded into the agents so all pipelines can use any internal buildkite plugin they want.

To achieve this, we have to do some architectural designs first.

### Designing the solution

First few questions will come up are:

1. How does that queue going to help us securing our infrastructure.
2. How can we protect the KMS key which is used to encrypt all the secrets.
3. How can we protect an internal bad actor from accessing those secrets.

The first question is relatively simple, we configure our agent deploy roles to only allow assume role from a specific queue. For example, only the EC2 instance in the `cde` stack will be able to assume the deploy role in our cde accounts. The `AssumeRolePolicyDocument` from the `DeployRole` will look like this:

```yaml
      AssumeRolePolicyDocument:
        Version: 2012-10-17
        Statement:
          - Effect: Allow
            Principal:
              AWS:
                - !Sub
                  - "arn:aws:iam::${TrustedAccountId}:role/buildkite-agents-${BuildkiteQueue}-Role"
                  - BuildkiteQueue: Fn::FindInMap: [Accounts, BuildkiteQueue, !Sub "${AWS::AccountId}"]
            Action: 'sts:AssumeRole'
```

Here, the `TrustedAccountId` is the ID of the tools account. and the value of the `BuildkiteQueue` would be one of `default`/`cde`/`infra`. So for cde account, the Principal will look like `"arn:aws:iam::111122223333:role/buildkite-agents-default-Role"`. In this way, we have defined a clear boundary as to which agent can access which account(s).

The seconds question is a bit harder to answer. Let's start by looking at all the IAM roles that have access to this KMS key, which lives in our tools account:

* `PowerUserRole` and `AdministratorRole`
* `agent-deploy-role`
* Any other Roles created by the agent-deploy-role

Moreover, the IAM permission of `agent-deploy-role` is a superset of that `PowerUserRole`. It can do a subset of IAM operations including `iam:UpdateAssumeRolePolicy`, `iam:PutRolePolicy` and `iam:DeletePolicy`. Also, if you are familiar with IAM, you will know that the default `PowerUserAccess` grant total control to KMS service. So if you allow someone to access that `agent-deploy-role`, he/she will be able to read those secrets. Can we do some restrictions of that `agent-deploy-role`? We can, but it will be hard to get it right, and it's not easy to keep a balance between being convenient and being secure. We have, however, decided not to do any restriction here, and put a restriction in our buildkite agent hook to forbid anyone from using the `infra` agent unless he/she is in the SRE team in buildkite and/or the pipeline is whitelisted. More on that later.

Now comes the third question, which is partially answered in our discussion of the second question. How can we establish boundaries that bad actors cannot access those secrets? We have used the following boundaries:

1. IAM, IAM is used to restrict which agent have access to the `infra` accounts(tools is one of them). The answer is only `infra` agents have access to the tools account.
2. Agent hook and SSM items. We have the agent hook in place to read settings from SSM, and based on the settings, only people in the SRE team and/or pipeline in a whitelist is allowed to use those `infra` agents.
3. BitBucket groups. Some of the critical repositories can only be access by the SRE team members.

We are certain that with these measures in place, it is not possible for a bad actor outside of SRE team to read those secrets.

### Implementing the solution: base stack

In order to make everything that we had planned run, we need to have a few resources:

1. An S3 bucket for our bootstrap scripts

2. KMS key for the encryption of the SSM items

3. three managed IAM policies for the instances, this is for the `ManagedPolicyARN` parameter when we build the buildkite stacks. The key difference between these policies is the ability to access ssm namespaces, for example, the policy for the `infra` agents will look like this:

   ```yaml
         - Effect: Allow
           Action:
             - 'ssm:GetParameter*'
           Resource:
             - !Sub "arn:aws:ssm:${AWS::Region}:${AWS::AccountId}:parameter/vendors/buildkite/infra/*"
         - Effect: Allow
           Action:
             - 'ssm:DescribeParameters'
           Resource:
             - !Sub "arn:aws:ssm:${AWS::Region}:${AWS::AccountId}:*"
         - Effect: Allow
           Action:
             - 'kms:Decrypt'
           Resource:
             - !GetAtt BuildkiteKey.Arn
   ```

It makes sense to build a base stack for these resources. So we made it come true.

### Implementing the solution: buildkite stacks

We had a helper script to create the buildkite stacks for us, which will mostly grab the spot history for us, so we can set a spot bid price automatically. With the help of this script, we can put all other Cloudformation stack parameters into a single file so each file will represent a Buildkite CI stack in AWS. Now that we have created a few more items in the base stack, we had extended that script a little bit to also grab the other pieces of information over and feed them into Cloudformation. We have re-used some of our old stack setting files and created a few more. We are really happy with this setup.

One thing to note here is, like many other Buildkite users, we have a separate `docker-builder` stack, the size of the ASG is set to 1 with 4 agents, that instance has a big disk and it will not stop so as to best cache our docker layers. We run all our docker builds on that instance. This instance cannot assume any deploy role in our setup and we are happy with it.

One last thing to mention here is we have proudly disabled the default S3 Secrets plugin by setting the `EnableSecretsPlugin` to "false" in all our parameter files.

### Implementing the solution: `bootstrap.sh`

In buildkite CI stack, you can specify an S3 path to a bootstrap script that will run every time a new instances comes up. We have done the following things in this script:

* Install some compatibility packages for Amazon Linux 1 instance: we do have that for historical reasons and we have to install `python36` and `amazon-ssm-agent` on these instances.
* Configure ssh to use port 443 to communicate with github: we have Nacl in place to stop SSH traffic via port 22, so we have used the trick discussed [here](https://help.github.com/en/github/authenticating-to-github/using-ssh-over-the-https-port).
* Do initial key scans. This is tricky because we have a `pre-checkout` hook that will try to initialize SSH connections, while the default key scan only happens at checkout stage.
* Setup our homebrew aws-paramstore-secrets plugin as secrets backend.
* Do a few more hardening things by `chown` a few files/directories so the `buildkite-agent` cannot modify them.

### Implementing the solution: aws-paramstore-secrets plugin

The repository can be found here: [https://github.com/mikeknox/aws-paramstore-secrets-buildkite-plugin](https://github.com/mikeknox/aws-paramstore-secrets-buildkite-plugin).

It's a bit untidy at the moment, and we are in need of more unit tests, but we have dog-fooded it in production for a while. But before you dive into this plugin, I would suggest you take a read at the following resources first:

* [https://buildkite.com/docs/agent/v3/securing](https://buildkite.com/docs/agent/v3/securing)
* [https://buildkite.com/docs/agent/v3/hooks](https://buildkite.com/docs/agent/v3/hooks)
* [An old version of bootstraps.sh](https://github.com/buildkite/agent/blob/v2.6.10/templates/bootstrap.sh). This is actually an early version of all the default hooks.

What we have completed is an agent hook that does not work as a normal Buildkite plugin, it is installed and configured at bootstrap time. It has all the following features that a normal Buildkite plugin does not have:

* The agent hook code can be owned by root, so no pipeline can change the agent hook source code since it is running as `buildkite-agent` user.
* Most of the time, agent hook cannot be configured in a pipeline, its aim is to prepare the runtime environment for a pipeline. Think of the original S3 based security agent hook, you cannot enable/disable the hook in your pipeline, it will just download the secrets/deploy keys for you.
* The proper way to update the agent hook code is to kill the instance and let the bootstrap script do it, although you need the AWS permission to go to that account to kill it. In comparison, it is much easier to update a plugin version in a pipeline, you can just change the version and Buildkite will download it for you.
* Except checkout and command hooks, agent hooks in general has a higher priority than the plugin/repo hooks. This means, agent hooks can be used to enforce some policy, and there's no way the pipeline can disable these policies.

What we want to achieve in this plugin can be summarized here:

* Retrieve deploy keys from parameter store.
* Add a project level deploy key for buildkite plugin repositories.
* Retrieve secrets from parameter store and export them as environment variables.
* Control who have access to the deploy keys and environment variables in some way.

#### hooks in the plugin

To achieve these goals, we have added several agent hooks, in the order of execution, we have:

* environment hook
* pre-checkout hook
* post-checkout hook
* pre-exit

##### Environment hook

We have done several things in the environment hook, most importantly, we run the python script that will do all the heavy-lifting for us, it will check access control list, look at several places for deploy keys and environment variables, export the environment variables and create ssh-agent for the deploy keys. Because we want to have a global ssh key for our Buildkite project, so we have to actually start multiple ssh agents, because putting all the deploy keys in one SSH agent will not work, [as discussed previously](https://blog.xiaket.org/2020/ssh-agent-multiple-deploy-keys.html). What we had done here is to create an SSH agent for that project level deploy key in this hook. In the python script, we will export that SSH agent pid/authentication socket to a different pair of environment variables (`AWS_PARAMSTORE_SECRETS_AGENT_PID` and `AWS_PARAMSTORE_SECRETS_AUTH_SOCK`). and later we will use that conditionally in the pre-checkout hook. As for the environment variables, we haven't done much, except we have used [`shlex.quote`](https://docs.python.org/3/library/shlex.html#shlex.quote) to make sure we handle complext quotes properly.

##### Pre-checkout hook

In most cases, when we are about to run the pre-checkout hook, we should have two ssh agents running, one for the global ssh key and the other for the repo that we want to checkout. As the buildkite plugin checkout process does not trigger the pre-checkout hook, all we need to do here is to swap the ssh agent with the default ssh agent that we have started for the plugins. In order to do that, we saved the pid/socket path of the SSH agent for the Buildkite plugin project to `ORIG_SSH_AGENT_PID` and `ORIG_SSH_AUTH_SOCK`, and tried a `git ls-remote` to see whether the alternative ssh agent can be used to checkout the code. If that's the case, we save them to `SSH_AGENT_PID` and `SSH_AUTH_SOCK`. They will be used in the checkout process.

##### Post-checkout hook

This is is straight forward, we restored `SSH_AGENT_PID` and `SSH_AUTH_SOCK ` to their original value and unset the `ORIG_` we had set in pre-checkout hook

##### Pre-exit

In this hook, we need to kill those two SSH agents and unset some environment variables. Trying to be a good citizen, you know.

#### Python script in the plugin

Enough about our hooks, let's talk about some of the details in the python script. In our setup, we read three sub-namespaces in parameter store:

* `/vendors/buildkite/{queue}/global`
* `/vendors/buildkite/{queue}/<repo-slug>`
* `/vendors/buildkite/{queue}/<pipeline-slug>`

For us, the `{queue}` is one of `default`, `cde` and `infra`. The pipeline slug is obtained from environment variable `BUILDKITE_PIPELINE_SLUG`. The repo slug is calculated from `BUILDKITE_REPO`. For example, if `BUILDKITE_REPO` is`https://github.com/buildkite/bash-parallel-example.git`, the calculated `repo-slug` will be `github.com_buildkite_bash-parallel-example.git`.

For deploy key, we actually only read that from the second namespace, because that's the only place it makes sense. More specifically, the sub-path is hard coded to be `ssh/key`, so in the github project mentioned above, the full path of the deploy key is `/vendors/buildkite/default/github.com_buildkite_bash-parallel-example.git/ssh/key`. If an SSH repository URL is provideed in `BUILDKITE_REPO`, for example, `ssh://git@your-scm.io:32200/hp/philosophers-stone.git` will lead to the full path that looks like: `/vendors/buildkite/default/your-scm.io-32200_hp_philosophers-stone.git/ssh/key`.

All environment variables are obtained from the `env` sub-namespace, and we will make it presentable as a normal environment variable, for example, `/vendors/buildkite/default/hermione/env/fav-lesson` will export `FAV_LESSON` to your pipeline named Hermione using the default queue. It is possible to create an environment variable for a repo as well, and if the same environment variable is defined both in the repo and pipeline level, the pipeline one will prevail.

Last but not the least, let's talk about how we handle the access control. We read two special values from each sub-namespace. For example, if you want to protect a repo level build time secret and decided that only two pipelines should have access to that value, you could define `allowed_pipelines` in that pipeline namespace with the value set to the two pipelines slug, separated by new line. That is, create an parameter store item with the path `/vendors/buildkite/{queue}/<repo-slug>/allowed_pipelines`, and value set to `slug21\nslug-2`.

As we've discussed before, the one buildkite agent we want to protect is `infra` . So, we defined parameter store item `/vendors/buildkite/infra/global/allowed_pipelines` with its value to be a list of all the infra pipelines. This will work, because when a bad actor runs the infra pipeline, the python script will try to read all the environment variables in that `global` sub-namespace, so it will read that value, and raise an exception because the current pipeline is not listed there.

#### Configuration of the plugin

We have 



















### Implementing the solution: a poor man's audit log

### Audit log

We are on the Standard plan in buildkite, which does not include audit log. With the new [Eventbridge notification](https://buildkite.com/docs/integrations/amazon-eventbridge) in place, we can setup the integration so all the events will be logged into Cloudwatch. From there, we can setup retention period for the logging, save to S3 and transfer to Sumologic. This will not cost us a lot and will give us the traceability that we lack at this stage.

### Case studies











### Cases

1. Have 