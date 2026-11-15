# Hosted demo

The prototype runs at https://d2v5b43xh6er8w.cloudfront.net.
Sign in with any account from the main README; every password is `welcome@123`.

## What runs where

All of it is in the AWS account behind the `deva-dev` profile, region us-east-1.

| Piece | Resource | Job |
|---|---|---|
| Link | CloudFront `E1695MI4SV0NTY` | One https address. Serves the screens, and forwards `/api/*` to the API with no caching. |
| Screens | S3 bucket `datalens-demo-378617177387` | The built frontend. Private; only CloudFront can read it. |
| Screen routes | CloudFront function `datalens-spa` (`spa-routes.js`) | Serves the app shell for addresses like `/roster`, so a refresh does not 404. |
| API | EC2 `i-0cedc7b885ad38166`, t3.micro, Amazon Linux 2023 | FastAPI under systemd (`datalens.service`), SQLite in `/opt/datalens/backend/data`. |
| Firewall | Security group `sg-0bad75f1bbb858b2c` | Port 8000 only from CloudFront. SSH only from the deploying machine's address. |

The API runs with `DATALENS_COOKIE_SECURE=1`, so the sign-in cookie only travels over https.
The copilot key lives in `/opt/datalens/.env` on the instance, readable only by the app's user.
SSH uses the key pair `datalens-demo`; its private key is in `~/.ssh/datalens-demo.pem` on the machine that created it.

## Update it

```
deploy/update.sh            # ship the current commit, keep the demo's data
deploy/update.sh --reset    # also restore the story to Tuesday 28 July, 18:00
```

If your address has changed, allow SSH from it first:

```
aws ec2 authorize-security-group-ingress --group-id sg-0bad75f1bbb858b2c --protocol tcp --port 22 --cidr <your-ip>/32
```

## Cost and shutdown

A t3.micro, a small disk and light CloudFront traffic come to a few dollars a month.
To stop it, disable and delete the distribution, empty and delete the bucket, and terminate the instance.
