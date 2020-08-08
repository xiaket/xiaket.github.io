---
title:  Delete default VPC in new Accounts using Stackset in a safe way
date:   2020-08-08 13:44
lang:   en
ref:    delete-default-vpc-using-stackset
---

Let me ask you a quick question, how do you remove the default VPCs in a newly created AWS account?

For a manually created AWS account, it doesn't hurt to do that manually. You just need to remove the subnets and the internet gateway in the VPC, then you can remove the VPC. However, you might want to do the same for all the regions in that account, or else you may end up having some colleagues that will use that default VPC by mistake which will cause a lot of headaches.

However, in many organizations, AWS accounts are created automatically. Therefore, we want to have a systematic and automatic way to remove the default VPCs. AWS already gave us a feature that can deploy code to newly created accounts, and that feature called stackset. Once you have deployed a stackset to an organizational unit, new accounts joining that organizational unit will have an instance of that stackset automatically. So, it is natural for us to try to delete the default VPC using stackset.

What do we need to remove the default VPC? The obvious answer is to use a lambda to do the heavy lifting and use a custom resource defined in the same stack to invoke the lambda. That's a hacky solution, and the major drawback is the role that you have used will be leftover there. As a consequence, any user in that account who can create a lambda function can use that role to remove all the things running in a VPC, which is rather dangerous. We may want to define some conditions in the IAM role to restrict this role, but there's no good condition to do it inside of a stackset. For example, if you are deploying a stack, you can specify an expiration timestamp so the role cannot be used after say five minutes, but we cannot do this for a stackset, where we cannot specify such a parameter. I dug into this problem and come up with an idea, we can have another lambda backed custom resource that can clean up the IAM roles, there are a few intricate details in this solution that I want to talk about here.

## High level overview of the solution

First, let's look at the solution from a high level, in this stackset template, we have the following solutions:

* VPCDeletionLambda
* VPCDeletionLambdaRole
* RoleCleanupLambda
* RoleCleanupLambdaRole
* DeleteAllVPCCustomResource
* CleanupRoleCustomResource

We need to make sure that the clean up of the roles will happen after `DeleteAllVPCCustomResource`, which means we to declare a dependency there so things will happen in the right order, that is:

1. Cloudformation will create the lambda roles and lambda functions.
2. Cloudformation will create `DeleteAllVPCCustomResource`, which in turn will call `VPCDeletionLambda` to delete all the VPCs.
3. Cloudformation will create `CleanupRoleCustomResource`, which will call `RoleCleanupLambda` to delete all the roles.

Here, things will get tricky, conceptually, we need this `RoleCleanupLambda` to be able to remove some roles, and we need it to be able to remove its own role, so we don't have a lambda role that can be assumed by other lambdas that can delete roles in IAM. However, this is not going to work. Because when we delete an IAM Role, we need to first delete all the inline policies and detach all the managed policies, then we delete the role itself. When we delete `RoleCleanupLambdaRole`, we will first delete all the policies, include the permission to delete the role, so at that point, we can no longer delete that role. Therefore, we must create another role in the lambda function, assume this role, and use this new role to neutralize the roles. I have used the word "neutralize" here because we cannot remove the `RoleCleanupLambdaRole`, but we need to remove all of its inline policy so it can run again when we update/delete the custom resource.

## Create a role in the lambda

Let's jump into the details. We need to create a role in this lambda, and we need to protect this role well since it has `iam:DeleteRole` action in it. Moreover, this role will be leftover in this account, because for the reason stated above, we cannot remove it. However, we do have the advantage to create this role programmatically, so here we go.

We define the `AssumeRolePolicyDocument` to be:

```
trust = {
    'Version': '2012-10-17',
    'Statement': {
        'Principal': {'AWS': boto3.client("sts").get_caller_identity()["Arn"]},
        'Effect': 'Allow', 'Action': 'sts:AssumeRole'
    }
}
```

That is, only the current session of the lambda role will be able to use this role, which is a good start. Then, in the inline policy section, we have defined:

```
policy = {
    "Version": "2012-10-17",
    "Statement": [
        {
            "Action": [
                "iam:DeleteRole",
                "iam:ListRolePolicies",
                "iam:ListAttachedRolePolicies",
                "iam:DetachRolePolicy",
                "iam:DeleteRolePolicy",
            ],
            "Effect": "Allow",
            "Condition":{
                "DateLessThan":{"AWS:EpochTime": str(int(datetime.now().timestamp()) + 300)},
            }
        }
    ]
}
roles = [f"arn:aws:iam::986658884542:role/{role}" for role in roles]
policy["Statement"][0]["Resource"] = roles + [lambda_role]
```

For the record, in the custom resource section, we have allowed the user to specify multiple roles. In the above Python code, the roles in the list comprehension come from that list. So here, in this inline policy, we have narrowed down the scope so that the new role can only manage these roles. Also, we have added a condition that the role will expire after 5 minutes. Please note here we have to specify the timestamp as a string, or else IAM will complain about it.

## Assume the role and neutralize the other roles

That's enough about the tightening of the new role. After we've created the role with this inline policy, we will assume the role, and neutralize the roles:

```
def cleanup_roles(roles):
    lambda_role = boto3.client('lambda').get_function_configuration(
        FunctionName = os.environ['AWS_LAMBDA_FUNCTION_NAME']
    )['Role']
    role = create_one_time_role(roles, lambda_role)
    while True:
        try:
            creds = boto3.client("sts").assume_role(
                RoleArn=role, RoleSessionName=PHYSICAL_RESOURCE_ID,
            )["Credentials"]
            break
        except ClientError:
            # Cannot assume a newly created role immediately.
            time.sleep(2)

    ## More code to neutralize roles.
```

One pitfall here: after you have created the new role, you cannot assume this role immediately, so we have used a loop here to retry. The code we have employed to neutralize the roles will look like:

```
iam = boto3.client(
    "iam",
    aws_access_key_id=creds["AccessKeyId"],
    aws_secret_access_key=creds["SecretAccessKey"],
    aws_session_token=creds["SessionToken"],
)
self_role_name = lambda_role.split("/")[-1]
response = iam.list_role_policies(RoleName=self_role_name)
for policy in response["PolicyNames"]:
    iam.delete_role_policy(RoleName=self_role_name, PolicyName=policy)

for role_name in roles:
    response = iam.list_role_policies(RoleName=role_name)
    for policy in response["PolicyNames"]:
        iam.delete_role_policy(RoleName=role_name, PolicyName=policy)

    response = iam.list_attached_role_policies(RoleName=role_name)
    for policy in response["AttachedPolicies"]:
        iam.detach_role_policy(
            RoleName=role_name, PolicyArn=policy["PolicyArn"],
        )
    iam.delete_role(RoleName=role_name)
    print(f"Removed {role_name}")
```

The `creds` here comes from the `assume_role` call in the last section. we use these credentials to create the new iam client, which will in turn use the new role. The `lambda_role` is the arn of the original lambda role(`RoleCleanupLambdaRole`), which is obtained from introspection. We need to remove the policies in this role, but not to remove the role itself, because we still need to run this function when we delete the custom resource. For the roles that come from the user input in the custom resource, we will remove the inline policies first, then detach the managed policies and finally remove the role.

## IAM Role assigned to `RoleCleanupLambdaRole`

Apart from the managed `AWSLambdaBasicExecutionRole`, we need to add two more inline policies to `RoleCleanupLambdaRole`:

```
      - PolicyName: create-cleanup-roles
        PolicyDocument:
          Version: 2012-10-17
          Statement:
            - Effect: Allow
              Action:
                - iam:CreateRole
                - iam:PutRolePolicy
              Resource:
                - !Sub "arn:aws:iam::${AWS::AccountId}:role/role-cleaner-*"
```

This one allows us to create a role in the lambda function. We had a prefix here to make it nice and clean. The next permission is to allow introspection within the function, alernatively, we can have the user to put the arn of the `RoleCleanupLambdaRole` as an input to the custom resource, but I feel that's exposing the internal implementation to the user and I'm not a big fan of that.

```
      - PolicyName: introspection
        PolicyDocument:
          Version: 2012-10-17
          Statement:
            - Effect: Allow
              Action:
                - lambda:GetFunctionConfiguration
              Resource:
                - !Sub "arn:aws:lambda:${AWS::Region}:${AWS::AccountId}:function:${AWS::StackName}-*"
```

## Final notes

There're a few more challenges here:

1. Cloudformation has a limit of 4k characters for inline Python/javascript code, given we have quite a lot of logic here, we need to be mindful of this limit.
2. Testing of this solution is hard, so what we've done is to create a Cloudformation template with dummy lambda and dummy lambda role. The test strategy is to deploy the stack and then remove it, the expected behaviour is both the deploy and the delete would work, also, the dummy roles will be removed when we deploy the stack, and the dangerous inline policy in the lambda role should have been removed. After the delete, the created temporary role should still be there.
