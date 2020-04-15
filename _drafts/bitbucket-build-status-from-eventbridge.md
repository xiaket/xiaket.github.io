# Bitbucket build status update from Buildkite via Eventbridge

Recently, we have migrated all our buildkite pipelines from one organization to another, so we had a chance to look back and improve our setup. One of the many things we've done differently this time is the build notification. What we are expecting from this feature is after a build has finished, our Bitbucket needs to know whether it's successful or not. We used to have a lambda function behind an AWS API Gateway, and this lambda will receive a post-build payload from Buildkite, do some transformation, then do another API call to update the build status in Bitbucket. This solution certainly had worked for us for quite some time, but we are not completely comfortable with this approach, in that we need to provide a publicly accessible API endpoint that has access to our repository. Buildkite had provided some protection by sending a unique token in the header that you can check, but in general, it still feels wrong.

When we set out to set up our Buildkite for the new organization this time, we are using a different approach. [Recently Buildkite announced their integration with AWS Eventbridge](https://buildkite.com/changelog/90-amazon-eventbridge-partner-integration), this means that we can get all the events from Buildkite without an explicit API endpoint. This certainly opens up lots of possibilities. And we took advantage of it and implemented a solution that involves only a lambda function receiving payload from Eventbridge, and we do filter in the rule so that only the "Build Started" and "Build Finished" events are sent to the lambda. And of course, we are deploying the solution via Cloudformation.

The logic in this lambda function should be straight forward to people who are familiar with this process, we get the detail information in the event, we do some transformation to get the payload that we are going to push to Bitbucket, and we send it. So the code should be looking like this.

```
def handler(event, context):
    detail = event["detail"]
    print(f"Detail: {detail}")

    payload = get_payload(detail)
    print(f"Payload: {payload}")

    url = f"https://scm.xxx.io/rest/build-status/1.0/commits/" + detail['build']['commit']

    request = urllib.request.Request(
        url,
        data=json.dumps(payload).encode('utf8'),
        headers={
          'content-type': 'application/json',
          'Authorization': f'Basic {get_auth()}'
        }
    )
    urllib.request.urlopen(request)
```

In this lambda handler, the event would look like what we have in [the example](https://buildkite.com/docs/integrations/amazon-eventbridge#events-build-started). In our production codebase, we have a check to verify that this lambda is getting the two expected events. Most likely, one more thing that you need to do here is to ignore a build that is triggered from Web UI with commit ID set to `HEAD`, as this does not make sense to [Bitbucket API](https://developer.atlassian.com/server/bitbucket/how-tos/updating-build-status-for-commits/). One last thing that we have chosen to do is to ignore `trigger_job`, as we have some pipelines that get triggered by the main build pipeline, they check out the same codebase, and we choose not to let these children interrupt what their parent is building. We will not talk much about the `get_payload` function in the code snippet above, because that's very Bitbucket specific and easy to implement. We are retrieving the Bitbucket access secrets from the AWS parameter store. So we need to define some extra permissions for the lambda role in our Cloudformation stack.

For now, our Cloudformation stack has two resources, one lambda role, and one lambda function. We do hope we can declare the rest of the solution using Cloudformation, but for now, that's not feasible, because AWS partner eventbridge does not even have cli support yet. Hence we have to do the rest of the setup manually. From now on, we will assume that you have [setup your Eventbridge integration in your AWS account](https://buildkite.com/docs/integrations/amazon-eventbridge#configuring).

In the AWS console, go to AWS Eventbridge, create a new rule that looks like this:

![eventbridge-setup-for-buildkite-build-events-1](/media/2020/eventbridge-setup-for-buildkite-build-events-1.png)

The second half of the rule setup should look like this:

![eventbridge-setup-for-buildkite-build-events-2](/media/2020/eventbridge-setup-for-buildkite-build-events-2.png)

As you can see, we just need to create the link between the partner eventbridge with the lambda we have created. After this, be sure to test your solution by triggering some builds in Buildkite and look at the logs in Cloudwatch. I don't believe this is mission-critical so I have not bothered to create a dead letter queue for the lambda, please feel free to add that to your setup if you feel otherwise.
