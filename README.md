<div align="center"><img src="assets/robot-chatbot-icon.jpg" style="width: 300px"></div>
<br>
<h1 align="center">🪫 Ptibot 🔋</h1>
<p align="center">My friendly little Python Discord Bot</p>

<div align="center">

![license](https://img.shields.io/github/license/leoraclet/ptibot)
![language](https://img.shields.io/github/languages/top/leoraclet/ptibot)
![lastcommit](https://img.shields.io/github/last-commit/leoraclet/ptibot)
<br>
![Language](https://img.shields.io/badge/Language-Python-1d50de)
![Libraries](https://img.shields.io/badge/Framework-Discord-fa8925)
![Size](https://img.shields.io/badge/Size-40Mo-f12222)
![OpenSource](https://badges.frapsoft.com/os/v2/open-source.svg?v=103)

</div>

> [!IMPORTANT]
>
> This project is currently a **work in progress** !

## Table of Contents
- [Table of Contents](#table-of-contents)
- [📖 About](#-about)
- [✨ Features](#-features)
- [🗂️ Structure](#️-structure)
- [📦 Dependencies](#-dependencies)
- [🛠️ Setup](#️-setup)
  - [📆 Google Calendar](#-google-calendar)
- [🚀 Run](#-run)
  - [🏠 System](#-system)
  - [🐳 Using Docker](#-using-docker)
- [🔥 Inspirations](#-inspirations)
- [💡 Tips \& Tricks](#-tips--tricks)
  - [SSL Certificates error](#ssl-certificates-error)
- [📜 License](#-license)

## 📖 About

**Ptibot** is a lightweight and extensible Discord bot built with Python, designed to help manage simple tasks, send reminders, and more—all within your Discord server.

Whether you're running a small community or developing a personal assistant, Ptibot provides a clean and developer-friendly starting point.

## ✨ Features

**Project**

- 🔄 **Reproducibility**: The project is built using [**uv**](https://docs.astral.sh/uv/), enabling seamless setup replication across different machines for consistent environments.

- 📖 **Well-Documented**: Source files include thorough comments and, where applicable, links and explanations to clarify key settings.

**Bot**

- ⌚ **Reminders**: Develop reminder handling (create, delete, etc.) with synchronization support for Google Calendar or other calendar services.

- 🤖 **ChatBot**: Implement a Chat Bot functionality by using the Mistral API under the hood.

> [!WARNING]
>
> Following is a list of features I **wish** to implement, and therefore, are **not yet features**:

- ✅ **Task Management**: Implement functionality to manage tasks (create, delete, mark as completed, etc.).

- 👣 **Github Tracking**: Develop a tracker to alert of events on repositories of connected account.

## 🗂️ Structure

> [!NOTE]
>
> The project's structure is designed to be self-explanatory, but here are the key components in case you're curious.

**Directories**

- [**`assets`**](./assets/) - Contains static image resources used in the project.
- [**`cogs`**](./cogs/) - Python modules categorized by functionality.
  - `admin.py` - Admin-related commands and logic.
  - `common.py` - Shared utility functions or commands.
- [**`db`**](./db/) - Contains the application's local database file.
- [**`ui`**](./ui/) - Contains custom UI components

**Files**

- `.dockerignore` - Specifies files and directories to exclude from Docker builds.
- `.env` - Environment variables for local development (not for production).
- `.env.template` - Template for required environment variables.
- `.gitignore` - Specifies files and directories to be ignored by Git.
- `.python-version` - Python version specification for tools like pyenv.
- `Dockerfile` - Defines the Docker image build instructions.
- `docker-compose.yml` - Docker Compose configuration file.
- `LICENSE` - Project license.
- `Makefile` - Automation commands for building, testing, and running the app.
- `README.md` - Project documentation and overview.
- `main.py` - Entry point of the application.
- `pyproject.toml` - Python environment and dependency configuration.
- `requirements.txt` - List of Python dependencies.
- `uv.lock` - Lockfile used by **uv** for reproducible environments.


## 📦 Dependencies

> [!NOTE]
>
> Here are the main libraries / dependencies of this project, but you can find all of them in the
> [`pyproject.toml`](./pyproject.toml) file.

- [**Loguru**](https://github.com/Delgan/loguru) - Python logging made(stupidly) simple
- [**discord.py**](https://github.com/Rapptz/discord.py) - An API wrapper for Discord written in Python.
- [**better-exceptions**](https://github.com/Qix-/better-exceptions) - Pretty and useful exceptions in Python, automatically.

## 🛠️ Setup

To use this app with your Discord bot, ensure the following prerequisites are met:

1. You have a Discord account.
2. You’ve created an application (and bot) through the [**Discord Developer Portal**](https://discord.com/developers).
3. You have access to your bot’s **TOKEN**.

After completing these steps, fill in the [`.env.template`](./.env.template) file with the necessary configuration details (such as the **TOKEN**) required by the app.

> [!CAUTION]
>
> Make sure to rename the file to `.env` so it is properly recognized by the application.


### 📆 Google Calendar

To enable synchronization with one of your Google Calendars, please follow this [guide](https://github.com/rempairamore/GCal2Discord/tree/main) and configure the environment variables as specified.


## 🚀 Run

If you'd like to run this bot on your machine, here are two versions of how to do so by either doing on your [**system**](#-system) or [**using docker**](#-using-docker).

### 🏠 System

First, make sure the [**`uv`**](https://docs.astral.sh/uv/getting-started/installation/) Python package manager is installed on your system.

Once that's done, clone the repository

```bash
git clone https://github.com/leoraclet/ptibot
cd ptibot
```

Then, install the project dependencies:

```bash
uv sync
```

> [!TIP]
>
> You may need to create a virtual environment beforehand:
> ```bash
> uv venv
> ```

Finally, if you have [**Make**](https://www.gnu.org/software/make/manual/make.html) installed, you can launch the development server accordingly.

```bash
make run
```

or you can just run simple commands using

```bash
uv run {YOUR_COMMAND}
```

### 🐳 Using Docker

Ensure that [**Docker**](https://docs.docker.com/get-started/introduction/get-docker-desktop/) is installed on your system and that the `docker` command is available in your terminal.

To start the Docker setup, run:

```bash
docker compose up -d
```

> [!TIP]
>
> To rebuild the image from scratch (without using the cache), use the following command:
>```bash
> docker compose build --no-cache
>```

As with local development, you can use the [**`Makefile`**](./Makefile) to manage Docker-related tasks easily with the following commands:

```bash
make up      # Build (if needed) and start the containers
make down    # Stop and remove containers and associated networks
make build   # Build or rebuild the Docker services
make logs    # View the output logs from running containers
```

## 🔥 Inspirations

These projects served as both inspiration and valuable references during the development of this one. Be sure to check them out if you're interested in learning more:

- [**Deadbeef**](https://github.com/0xf1d0/deadbeef/) – A Discord bot created by a friend for a cybersecurity school server.
- [**discord-reminder-bot**](https://github.com/TheLovinator1/discord-reminder-bot) – A bot for managing reminders and TODO tasks.
- [**Python-Discord-Bot-Template**](https://github.com/kkrypt0nn/Python-Discord-Bot-Template) – A helpful template for setting up Discord bots with Python.
- [**GCal2Discord**](https://github.com/rempairamore/GCal2Discord) - Syncs events from a Google Calendar to a Discord server


## 💡 Tips & Tricks

### SSL Certificates error

If you encounter an error similar to the following:

```bash
...

ssl.SSLCertVerificationError: [SSL: CERTIFICATE_VERIFY_FAILED] certificate verify failed: unable to get local issuer certificate (_ssl.c:1010)
```

You can resolve this by installing [`pip-system-certs`](https://pypi.org/project/pip-system-certs/) in your virtual environment. To do so, run:

```bash
uv add pip-system-certs
```

> [!CAUTION]
>
>If this solution doesn't work for any reason, you can find alternative solutions [**here on Stack Overflow**](https://stackoverflow.com/questions/51925384/unable-to-get-local-issuer-certificate-when-using-requests).

## 📜 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.