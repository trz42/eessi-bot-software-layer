A bot to help with requests to add software installations to the [EESSI software layer](https://github.com/EESSI/software-layer)

GitHub App implemented in ``eessi_bot_software_layer.py``

Script to start app: ``run.sh``

Requires:

* Python 3
* **PyGitHub**: Python library to use GitHub API v3
  * https://github.com/PyGithub/PyGithub
  * API: https://pygithub.readthedocs.io/en/latest/reference.html
* **Waitress**: production-quality pure-Python WSGI server
  * https://docs.pylonsproject.org/projects/waitress/en/stable/
* **PyGHee**: Python library to facilitate creating a GitHub App implemented in Python
  * https://github.com/boegel/PyGHee

```
pip3 install --user -r requirements.txt
```

# Detailed instructions to set up development environment

The following sections describe and illustrate the steps necessary to set up the development environment for the EESSI bot.

## Prerequisites

- GitHub account
- GitHub repository on whose events the bot shall react to
- Linux machine where the EESSI bot shall run (some steps may require sudo access)

## Step 1: Smee.io channel and smee client

We use smee.io as a service to relay events from GitHub to the EESSI bot. To do so, create a new channel on the page https://smee.io and note the URL, e.g., https://smee.io/CHANNEL_ID

On the Linux machine which runs the EESSI bot we need a tool which receives events relayed from https://smee.io/CHANNEL_ID and forwards it to the EESSI bot. We use the Smee client for this. The Smee client can be installed globally with

```
npm install -g smee-client
```

or per user

```
npm install smee-client
```

If you don't have `npm` on your system and don't have sudo access to easily install it, you may use a container as follows

```
mkdir smee
cd smee
singularity pull docker://node
singularity exec node_latest.sif npm install smee-client
cat << EOF > smee
#!/usr/bin/env bash

BASEDIR=$(dirname "$0")

singularity exec $BASEDIR/node_latest.sif $BASEDIR/node_modules/smee-client/bin/smee.js "$@"
EOF

chmod 700 smee
export PATH=$PATH:$PWD
```

Finally, run the Smee client as follows

```
smee --url https://smee.io/CHANNEL_ID
```

Alternatively, you may use a container providing the smee client. For example,

```
singularity pull docker://deltaprojects/smee-client
singularity run smee-client_latest.sif --url https://smee.io/CHANNEL_ID
```

## Step 2: Registering GitHub App

We first need to register a GitHub App, link it to the Smee.io channel, set a secret token to verify the webhook sender, set some permissions for the app, subscribe it to selected events and define that this app should only be installed in your account.

At the [app settings page](https://github.com/settings/apps) click "New GitHub App" and fill in the page, particular the following fields
- GitHub App name: give the app a name of you choice
- Homepage URL: use the Smee.io channel (https://smee.io/CHANNEL_ID) created in Step 1
- Webhook URL: use the Smee.io channel (https://smee.io/CHANNEL_ID) created in Step 1
- Webhook secret: create a secret token which is used to verify the webhook sender
- Permissions: assign permissions to the app it needs (e.g., read access to commits, issues, pull requests); those can be changed later on; some permissions (e.g., metadata) will be selected automatically because of others you have chosen
- Events: subscribe the app to events it shall react on (e.g., related to pull requests)
- Select that the app can only be installed by this (your) GitHub account

Click on "Create GitHub App"

## Step 3: Installing GitHub App (might trigger first event to EESSI bot)

You need to install the GitHub App -- essentially telling GitHub to link the app to an account and one, several or all repositories on whose events the app then should act upon.

Go to the page https://github.com/settings/apps and select the app you want to install by clicking on the icon left to the apps name or on the "Edit" button right to the name of the app. On the next page you should see the menu item "Install App" on the left-hand side. When you click on this you should see a page with a list of accounts you can install the app on. Choose one and click on the "Install" button next to it. This leads to a page where you can select the repositories on whose the app should react to. Select one, multiple or all and click on the "Install" button.

## Step 4: Installing the EESSI bot on Linux machine

The EESSI bot for the software layer is available from https://github.com/EESSI/eessi-bot-software-layer

Get the EESSI bot onto the Linux machine by running something like

```
git clone https://github.com/EESSI/eessi-bot-software-layer.git
```

If you want to develop the EESSI bot, it is recommended that you fork the repository and use the fork on the Linux machine.

The EESSI bot requires some Python packages to be installed. See the top of this page, or simply run (the `requirements.txt` file is provided by the EESSI bot repository)
```
pip3 install --user -r requirements.txt
```

**Troubles installing some of the requirements?**
You may try to install some of the dependencies by fixing their version. For example, on the CitC cluster (https://github.com/EESSI/hackathons/tree/main/2021-12/citc) installing PyGithub failed due to some problem installing its dependency PyNaCl. Apparently, PyGithub only required version 1.4.0 of PyNaCl but the most recent version 1.5.0 failed to install. Hence, when installing PyNaCl version 1.4.0 first, then PyGithub could be installed. Example commands

```
pip3 install --user PyNaCl==1.4.0
pip3 install --user -r requirements.txt
```

### Step 4.1 Using the development version of PyGHee

The above command `pip3 install --user -r requirements.txt` installs the latest release of the PyGHee library. If you want to use the development version, i.e., what is available from GitHub or your own local copy, you have to set `PYTHONPATH` correctly. Assume the library's main directory is `SOME_PATH/PyGHee` then do the following in the terminal/shell/script where you run the bot:

```
export PYTHONPATH=SOME_PATH/PyGHee
```

## Step 5: Configuring and running EESSI bot on Linux machine

You need to set up two environment variables: `GITHUB_TOKEN` and `GITHUB_APP_SECRET_TOKEN`.

### Step 5.1: GitHub Personal Access Token (PAT)

Create a Personal Access Token (PAT) for your GitHub account via the page https://github.com/settings/tokens where you find a button "Generate new token".
Give it meaningful name (field titled "Note") and set the expiration date. Then select the scopes this PAT will be used for. Then click "Generate token". On the result page, take note/copy the resulting token string -- it will only be shown once.

On the Linux machine set the environment variable `GITHUB_TOKEN`, e.g.
```
export GITHUB_TOKEN='THE_TOKEN_STRING'
```

### Step 5.2: GitHub App Secret Token
The GitHub App Secret Token is used to verify the webhook sender. You should have created one already when registering a new GitHub App in Step 1.

On the Linux machine set the environment variable `GITHUB_APP_SECTRET_TOKEN`, e.g.
```
export GITHUB_APP_SECRET_TOKEN='THE_SECRET_TOKEN_STRING'
```
Note, depending on the characters used in the string you will likely have to use single quotes when setting the value of the environment variable.

### Step 5.3: Create a private key and store it on the Linux machine
The private key is needed to let the app authenticate when updating information at the repository such as commenting on PRs, adding labels, etc. You can create the key at the page of the GitHub App you have registered in Step 1.

Open the page https://github.com/settings/apps and then click on the icon left to the name of the GitHub App for the EESSI bot or the "Edit" button for the app. Near the end of the page you will find a section "Private keys" where you can create a private key by clicking on the button "Generate a private key". The private key should be automatically downloaded to your local computer. Copy it to the Linux machine and note the full path to it.

### Step 5.4: Obtain bot repository

The bot needs a few scripts. These and an example configuration file are provided by the repository [EESSI/eessi-bot-software-layer](https://github.com/EESSI/eessi-bot-software-layer) (or your fork of it).

First, clone the EESSI/eessi-bot-software-layer repository (or your fork of it) by running

```
git clone https://github.com/EESSI/eessi-bot-software-layer.git
```

### Step 5.5: Create the configuration file `app.cfg`

After cloning the bot's repository, change directory with `cd eessi-bot-software-layer` and note the full path of the directory (`pwd`).

If there is no `app.cfg` in the directory, create an initial version from `app.cfg.example`.

```
cp -i app.cfg.example app.cfg
```

Now set some values as follows:

```
private_key = FULL_PATH_TO_PRIVATE_KEY
build_job_script = PATH_TO_BOT_REPO/scripts/eessi-bot-build.slurm
```

### Step 5.6: Run the EESSI bot

Change directory to `eessi-bot-software-layer` (which was created by cloning the repository in Step 5.4 - either the original one from EESSI or your fork). Then, simply run the bot by executing
```
./run.sh
```

Note, if you run the bot on a frontend of a cluster with multiple frontends make sure that both the Smee client and the bot run on the same machine.

The bot will log events into the file `pyghee.log`.

## Testing EESSI bot

The easiest test may be a change -- creating a branch, committing a change, creating a pull request, etc -- to one of the repositories you have selected when installing the app in Step 3. Which events may be forwarded depends on which events you have subscribed the app to when you registered the app in Step 2.
