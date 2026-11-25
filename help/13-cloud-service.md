# ☁️ Cloud service

The cloud service lets the users of a PhotoMigrator Web Interface run a migration or a Takeout processing **on the server**, without installing PhotoMigrator and without free disk space on their own computer. It is optional and off by default: a self-hosted installation keeps working exactly as before, and every feature stays free.

When the server owner adds Stripe keys, tasks are paid by remote users (administrators never pay). Without Stripe keys every task is free.

---

## For users: `My tasks`

When the service is enabled, the sidebar shows `Cloud service > My tasks` with the list of your tasks, their state and the next step.

### Types of task
| Task | What it does | When you pay |
|---|---|---|
| **Takeout → my cloud** | Processes a Google or iCloud Takeout and uploads it to Immich Photos, Synology Photos, NextCloud Photos or Google Photos. | When you accept the quote. |
| **Fix my Takeout** | Processes a Google or iCloud Takeout and lets you download the result. | When the result is ready (needed to download it). |
| **Cloud → cloud** | Moves a library from Immich Photos, Synology Photos or NextCloud Photos to another service. Google Photos cannot be a source (its API only lets apps read what they uploaded themselves). | When you accept the quote. |

### Steps
1. `New task`: choose the type of task, the Takeout type (Google or iCloud), how you send the files and the destination with its credentials, and accept the terms of service and the privacy policy.
   - Credentials: `Use my saved account` copies an account of `Settings > Service credentials` into the task (your saved account is not changed), or `Enter them for this task only`. The destination server must be reachable from the internet. Create an API key (Immich) or an app password (NextCloud) just for the task and revoke it when it ends.
2. Send your Takeout:
   - `Upload from this browser`: drop the ZIP files. Uploads are sent in parts and resume if the connection drops: add the same file again to continue.
   - `Import from Dropbox` / `Import from OneDrive` (when the server offers them): in Google Takeout choose "Add to Dropbox" or "Add to OneDrive", then connect the storage (read-only) and choose the folder with the files.
3. `Check and get a quote`: PhotoMigrator checks that the uploaded ZIP files can be opened and contain photos or videos (a Takeout compressed again into another ZIP is accepted), measures the data and tests the destination (Immich and NextCloud: a tiny test image is uploaded and deleted; Synology: sign-in and read access; Google Photos: the token can upload). You get the quote by email: size, price, estimated start and duration. A quote is valid for 7 days.
4. Pay with Stripe (or `Start` when the task is free). The task joins the queue; you get an email when it starts and when it ends, and you can follow it live in `Activity`.
5. Result:
   - Migrations end with an email confirming that the data and credentials were deleted.
   - A processed Takeout is downloaded in ZIP parts of up to 50 GB. Downloads resume if they stop (`Copy link` gives a link for a download manager). The result is deleted after 7 days (you get a reminder 2 days before).

### Price, refunds and cancellation
- 5 € minimum per task, then 5 cents per GB, VAT included (the server owner can change these values).
- If a task fails, the full amount is refunded automatically. A task that ends without any photo or video to deliver counts as failed, so it is never charged.
- Canceling a task before it starts refunds the full amount. A task that has started can be stopped, but it is not refunded.

### How your data is protected
- Each task has its own temporary folder (`<data>/.service-work/<task>`). No user can browse it: the name `.service-work` is reserved and cannot be used as a user folder.
- The credentials of a task are encrypted with a key that exists only inside that folder. When the task ends, fails, is canceled or its download expires, the folder is deleted, so the credentials can never be read again. The deletion is recorded in the task history and confirmed by email.
- Task files and credentials are outside the Web Interface database, so they are never part of its backups.
- Card details are entered on the Stripe page and never reach the server.
- PhotoMigrator only reads the source and never deletes anything in it.

---

## For the server owner

### Enable the service
`Administration Panel > Cloud service`:
- `Enabled`, prices, tasks run at a time, working space per task (10 TB by default, which fits a Takeout of about 3 TB), download speed limit (100 Mbps by default, shared by every download), download days and quote validity.
- `Operator name` and `Contact email`, shown in the terms of service (`/terms`) and the privacy policy (`/privacy`). These pages are templates: have them reviewed before charging users. The contact email also gets an email every time a user creates a task, with a button that opens the task in the Administration Panel.
- The tab also lists every task with its user, size, payment and state, the queue, the revenue and refunds, and the free disk space. `Cancel` refunds tasks that have not started; a running task can be canceled with or without a refund. `Refund` returns the payment of a finished task.

Tasks run one after another (or several at a time if you allow it). A task starts only when the volume has free space for it, and it is stopped (and refunded) if it uses more than the space per task. If the server restarts, interrupted tasks go back to the queue.

### Payments with Stripe
1. Create a Stripe account at https://dashboard.stripe.com/register and complete the activation. Until then you can use the test mode.
2. `Settings > Business > Public details`: business name, support email and statement descriptor (`PHOTOMIGRATOR`). `Settings > Branding`: logo and colour.
3. `Settings > Payment methods`: keep Card, Apple Pay and Google Pay. PhotoMigrator asks Checkout for card payments only (Apple Pay and Google Pay are included), so other methods of the account, such as SEPA Direct Debit, can stay on.
4. `Settings > Customer emails`: turn on receipts for successful payments and refunds.
5. Optional: `Settings > Tax` (Stripe Tax) and tick `Calculate VAT with Stripe Tax` in the Administration Panel. Prices then include VAT.
6. `Developers > API keys > Create restricted key` with **Write** access to Checkout Sessions and Refunds (nothing else is needed). Copy the key (`rk_test_…`).
7. `Developers > Webhooks > Add endpoint`: URL `https://<your server>/api/service/stripe/webhook` (the Administration Panel shows it), events `checkout.session.completed` and `charge.refunded`. Copy the signing secret (`whsec_…`).
8. Paste both in `Administration Panel > Cloud service`, save and press `Test connection`. Pay a test task with the card `4242 4242 4242 4242`.
9. To go live, repeat steps 6 and 7 in live mode and replace the key and the secret.

**Shared Stripe account.** The account can also be used by other businesses. Every Checkout session and payment of the cloud service carries the metadata `service=photomigrator`, the webhook answers `200` and ignores any event without it, and the card statement shows your account prefix followed by `PHOTOMIGRATOR` (for example `JTG* PHOTOMIGRATOR`).

### Import from Dropbox (optional)
1. https://www.dropbox.com/developers/apps → `Create app` → `Scoped access` → **Full Dropbox** (Takeout saves the files outside the app folder).
2. `Settings > OAuth 2 > Redirect URIs`: `https://<your server>/api/service/oauth/dropbox/callback`.
3. `Permissions`: `account_info.read`, `files.metadata.read`, `files.content.read`, and submit.
4. Paste the **App key** and **App secret** in the Administration Panel. In development status the app accepts up to 500 users; apply for production when you need more.

### Import from OneDrive (optional)
1. https://entra.microsoft.com → `Applications > App registrations > New registration`, account types **"Accounts in any organizational directory and personal Microsoft accounts"**, redirect URI (platform Web) `https://<your server>/api/service/oauth/onedrive/callback`.
2. Copy the **Application (client) ID**.
3. `Certificates & secrets > New client secret` (24 months) and copy its **Value**. Renew it before it expires.
4. `API permissions > Microsoft Graph > Delegated`: `Files.Read`, `offline_access`, `User.Read`.
5. Paste the Client ID and the secret in the Administration Panel.

### Environment variables
Every key can also be set in the `.env` file of Docker instead of the Administration Panel (the environment variable wins):

| Variable | Use |
|---|---|
| `PHOTOMIGRATOR_SERVICE_ENABLED` | `true` turns the service on. |
| `PHOTOMIGRATOR_SERVICE_WORK_DIR` | Folder of the task folders (default `/app/data/.service-work`). |
| `PHOTOMIGRATOR_STRIPE_SECRET_KEY`, `PHOTOMIGRATOR_STRIPE_WEBHOOK_SECRET` | Stripe restricted key and webhook signing secret. |
| `PHOTOMIGRATOR_DROPBOX_APP_KEY`, `PHOTOMIGRATOR_DROPBOX_APP_SECRET` | Dropbox app. |
| `PHOTOMIGRATOR_ONEDRIVE_CLIENT_ID`, `PHOTOMIGRATOR_ONEDRIVE_CLIENT_SECRET` | Microsoft app. |

Set `PHOTOMIGRATOR_WEB_PUBLIC_URL` so the links of the emails, Stripe and the OAuth redirects use your public address.

---

## 🏠 [Back to Main Page](../README.md)
