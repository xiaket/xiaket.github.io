---
title:  Delete default VPC in AWS Accounts using Stackset in a safe way
date:   2020-08-08 13:44
lang:   en
ref:    delete-default-vpc-using-stackset
---

Let me ask you a quick question, how do you remove the default VPCs in a newly created AWS account?

For a manually created AWS account, it doesn't hurt to do that manually. You just need to remove the subnets and the internet gateway in the VPC, then you can remove the VPC. However, you might want to do the same for all the regions in that account, or else you may end up having some colleagues that will use that default VPC by mistake which will cause a lot of headaches.

However, in many organizations, AWS accounts are created automatically. Therefore, we want to have a systematic and automatic way to remove the default VPCs. AWS already gave us a feature that can deploy code to newly created accounts, and that feature called stackset. Once you have deployed a stackset to an organizational unit, new accounts joining that organizational unit will have an instance of that stackset automatically. So, it is natural for us to try to delete the default VPC using stackset.

What do we need to remove the default VPC? The obvious answer is to use a lambda to do the heavy lifting and use a custom resource defined in the same stack to invoke the lambda. That's a hacky solution, and the major drawback is the role that you have used will be leftover there. As a consequence, any user in that account who can create a lambda function can use that role to remove all the things running in a VPC, which is rather dangerous. We may want to define some conditions in the IAM role to restrict this role, but there's no good way to do it inside of a stackset. For example, if you are deploying a stack, you can specify an expiration timestamp so the role cannot be used after say five minutes, but we cannot do this for a stackset, where we cannot specify such a parameter. I dug into this problem and come up with an idea, we can have another lambda backed custom resource that can clean up the IAM roles, there are a few intricate details in this solution that I want to talk about here.

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
3. Cloudformation will create `CleanupRoleCustomResource`, which will call `RoleCleanupLambda` to cleanse all the roles.

Here, things will get tricky, conceptually, we need this `RoleCleanupLambda` to be able to delete some roles, and we need it to be able to remove its own role, so we don't have a lambda role that can be assumed by other lambdas that can delete roles in IAM. However, this is not going to work. Because when we cleanup an IAM Role, we need to first delete all the inline policies and detach all the managed policies, then we delete the role itself. When we delete `RoleCleanupLambdaRole`, we will first delete all the policies, include the permission to delete the role, so at that point, we can no longer delete that role. Therefore, we must create another role in the lambda function, assume this role, and use this new role to neutralize the roles. This would be a rather deep rabbit hole. Also, if the roles are removed, an error will be raised when we delete the custom resouce, because without the role, Cloudformation will not be able to run the lambda again. Meanwhile, if we take a step back and look at the big picture, what we want to do is to remove the inline policies in that `VPCDeletionLambdaRole`. So during the role cleanup process, we can first cleanup the other lambda roles, removing their inline policy, then list the inline policies of the current lambda and remove that. 

## Permissions in `RoleCleanupLambdaRole`

Apart from the managed `AWSLambdaBasicExecutionRole`, we need to add two more inline policies to `RoleCleanupLambdaRole`:

```
- PolicyName: cleanup-roles
  PolicyDocument:
    Version: 2012-10-17
    Statement:
      - Effect: Allow
        Action:
          - iam:ListRolePolicies
          - iam:DeleteRolePolicy
        Resource:
          - !Sub "arn:aws:iam::${AWS::AccountId}:role/${AWS::StackName}-*"
```

We had assumed here that we are following the good practice of not to create a named IAM role unless we have to. We allow this `RoleCleanupLambdaRole` to list and remove all inline policies of all the roles created in this stack. The next permission is to allow introspection within the function. Alternatively, we can have the user to put the arn of the `RoleCleanupLambdaRole` as an input to the custom resource, but I feel that's exposing the internal implementation to the user and I'm not a big fan of that.

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

## Role cleanup process

The core logic will be something like this:

```
lambda_role = boto3.client('lambda').get_function_configuration(
    FunctionName = os.environ['AWS_LAMBDA_FUNCTION_NAME']
)['Role']
iam = boto3.client("iam")

self_role_name = lambda_role.split("/")[-1]
for role_name in roles + [self_role_name]:
    response = iam.list_role_policies(RoleName=role_name)
    for policy in response["PolicyNames"]:
        iam.delete_role_policy(RoleName=role_name, PolicyName=policy)

    print(f"Finished cleanup inline policy in {role_name}.")
```

Here, the `lambda_role` would be the arn of the original lambda role(`RoleCleanupLambdaRole`), which is obtained from introspection. We need to remove all the inline policies in all the roles, but not the roles themselves. Moreover, we need to cleanup the `RoleCleanupLambdaRole` as the last step. The `roles` here will be the list of roles that we need to cleanup, this is coming from the custom resource definition:

```
CleanupRoles:
  Type: 'Custom::CleanupRoles'
  DependsOn: DeleteDefaultVPC
  Properties:
    ServiceToken:
      !GetAtt RoleCleanupLambda.Arn
    Roles:
      - !Ref DeleteDefaultVPCLambdaRole
```

## A few last notes

1. If we have a named IAM role in the stack and we need to clean it up, we need to adjust the IAMRoles so our cleanup lambda have permission to cleanse it.
2. If you take another step back, I believe this solution can be used to run one-off, relatively easy AWS operations using Cloudformation. Please note it's an abuse though. :)