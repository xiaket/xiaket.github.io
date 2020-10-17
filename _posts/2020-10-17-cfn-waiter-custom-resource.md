---
title:  Generic waiter custom resource
date:   2020-10-17 21:43
lang:   en
ref:    cfn-waiter-custom-resource
---

In this article, I would like to share a pattern that we've employed to untangle the dependency between Cloudformation stacks/stacksets.

The best way to set up a new AWS account is to drop it into an organization unit(OU), and have various stacksets deployed to that OU. In this way, the new account will quickly pick up the configurations that we have planned for it. However, one of the annoyances of using stackset is the dependency between stacksets. For example, we would like to have one stackset to enable AWS Config for all accounts/regions, then have another stackset to deploy the custom config rule and yet another stackset for the conformance packs, the latter two stacksets depends on the deployment of the first stackset. However, when stackset instances are deployed to the new account, Cloudformation will ignore this dependency, and quite possibly the deployment of the second/third stackset will fail because the first one has not finished deployment. We resolved this dependency issue using a lambda based custom resource, which is pretty generic in that most of the cases you can apply the snippet to your Cloudformation template without modification. We will not talk about the basics of Custom Resource in Cloudformation here, please refer to [the official documentation](https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/template-custom-resources.html) for details.

In the following example, we need to create an event rule for an eventbridge that is created in another stackset. We would like to write an `!ImportValue` and get the name of the eventbridge like this:

```
  SomeRule:
    Type: AWS::Events::Rule
    Properties:
      EventBusName: !ImportValue stackset-event-bridge-name
      EventPattern:
        account:
          - !Ref SomeAccountId
      State: ENABLED
      Targets:
        - Arn: !GetAtt SomeLambda.Arn
          Id: run-some-lambda
```

And this stackset is likely to fail because the checking of the `!ImportValue` items is done before the deployment. We could pass in the name of the eventbridge as a template parameter no doubt, but the deployment may still fail if the eventbridge is not created at the time we create this rule. Logically, we would like to wait there until the eventbridge is ready. So it is natural to think of a lambda that can list all the eventbridge buses and do the waiting. However, the drawback of this approach is the lack of generality: for each service type, we have to write some logic to do the query, also we need to change the permission in the lambda role to grant that access. So instead, what we have done here is to ask the user to provide an export name like this:

```
  Waiter:
    Type: 'Custom::WaitResources'
    Version: '1.0'
    Properties:
      ServiceToken:
        !GetAtt WaiterLambda.Arn
      WaitingFor:
        - Id: Eventbridge
          ExportName: stackset-infra-event-bridge-name
```

The advantages are threefold:

1. We can pretty much fix the lambda role for this WaiterLambda. The only policy we need there is:

```
      - PolicyName: allow-list-stack-exports
        PolicyDocument:
          Version: 2012-10-17
          Statement:
            - Effect: Allow
              Action:
                - cloudformation:ListExports
              Resource: '*'
```

2. We can apply the same logic to all the queries, which means we don't have to change the code in our lambda function as well.
3. We can wait on multiple things and return the value of the exports in this custom resource. As an example, As an example, we can change our earlier eventbridge rule to:

```
  SomeRule:
    Type: AWS::Events::Rule
    Properties:
      EventBusName: !GetAtt Waiter.Eventbridge
      EventPattern:
        account:
          - !Ref SomeAccountId
      State: ENABLED
      Targets:
        - Arn: !GetAtt SomeLambda.Arn
          Id: run-some-lambda
```

Here, the `.Eventbridge` attribute is returned in the response object [as described here](https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/crpg-ref-responses.html). The full lambda code should be of little interest to everyone. However, I would like to present the function that handles the Cloudformation `CREATE` event here:

```
def create(event):
    data = {}
    while True:
        for resource in event["ResourceProperties"]["WaitingFor"]:
            export_name = resource["ExportName"]
            export_id = resource["Id"]
            exports = get_exports()
            logging.info(f"Current exports: {exports}.")
            if export_name in exports:
                data[export_id] = exports[export_name]
        if len(data) == len(event["ResourceProperties"]["WaitingFor"]):
            logging.info(f"All exports are found: {data}")
            break

        logging.info("Some exports are not found. Current data: {data}")
        time.sleep(30)

    return {
        "status": "SUCCESS",
        "PhysicalResourceId": "cfn-waiter",
        "Data": data,
    }
```

It's quite straightforward: we have a dead loop that will look at all the stack exports every 30 seconds, and if all the exports are found in the exports, we will break this loop and return the value of the exports in a dictionary. Although we have not shown the source code of that `get_exports` function here, it should be easy to implement, and the only advice here is not to forget the pagination of exports.

Finally, a few caveats for this solution:

1. It is to be noted that we are not using `!ImportValue` and the lower stack can be modified/removed, which may cause the upper stack to cease function properly.
2. It is advised to set the timeout of the lambda function to 900 seconds(the maximum). We have every belief that the deployment of the stacksets should finish before this timeout, but as far as I know there's no SLA on it. It's a good enough approach, not a silver bullet.