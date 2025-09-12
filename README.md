## Table of Contents

- [Repository Setup](#repository-setup)
- [Prerequisites](#prerequisites)
- [Opening the Development Environment](#opening-the-development-environment)
- [Filesystem Considerations](#filesystem-considerations)
- [Building the Workspace](#building-the-workspace)
- [Running the GUI](#running-the-gui)

# Repository Setup

> [!TIP]
> Before starting development, it is recommended to create a personal copy of this repository. This ensures privacy and allows you to push code to your own workspace.

> [!WARNING]
> Avoid publishing sensitive credentials (e.g., GitHub, Azure, or other API keys) in a public repository. Service providers may automatically detect and revoke compromised keys.

1. On GitHub, click on the **“+”** button (`Create new...`) in the top-right corner.
2. Select **Import repository**.
3. Paste the following repository link:  
   `https://github.com/gdesimone97/cogrob_pepper_nodes.git`
4. Configure the repository as **private**.
5. Complete the import process.

---

# Prerequisites

1. **Docker Engine**: [Installation guide](https://docs.docker.com/engine/install/)  
2. **Visual Studio Code (VS Code)**: [Installation guide](https://code.visualstudio.com/)  
3. **Dev Container Extension for VS Code**: [Installation guide](https://code.visualstudio.com/docs/devcontainers/containers)  

---

# Opening the Development Environment

1. Clone the repository on your local machine.
2. In VS Code, press `F1` → select **Build and Reopen in Container**.
3. Choose the configuration corresponding to your operating system:
   - Windows / macOS
   - Linux
4. Wait until the container build process completes.

---

# Filesystem Considerations

When running a Docker container, the filesystem is virtualized and isolated from the host machine.  
To enable persistence, specific directories can be mounted between the host and container. Any modifications in these linked directories are reflected in both environments.

In this setup, the working directory is automatically mounted inside the container at `/workspace` (see [Opening the Development Environment](#opening-the-development-environment)).

> [!CAUTION]
> Rebuilding the container resets its internal filesystem. Only data stored in mounted directories (e.g., `/workspace`) will persist.

---

## Useful Commands

Access the VS Code command menu by either:
- Pressing `F1`
- Using `Ctrl` + `Shift` + `P`

Relevant commands:
- **Build and Reopen in Container**: Rebuilds the container image and reopens it in VS Code.  
- **Reopen in Container**: Reopens the previously built container without rebuilding.  

---

## Customizing the Development Container

Different `devcontainer.json` files are provided depending on the operating system.  
For example, the configuration for Windows/macOS is located at:  
[.devcontainer/windows_mac/devcontainer.json](.devcontainer/windows_mac/devcontainer.json)

This file defines:
- User privileges  
- Workspace mounting  
- Installed VS Code extensions  
- Post-build commands  

By default, the image is built from [Dockerfile](.devcontainer/Dockerfile), which is initially empty.  
To permanently include additional packages, extend this Dockerfile by adding installation commands. Example:

```dockerfile
RUN apt update && apt install -y gedit
```

or:

```dockerfile
RUN pip install httpx
```

> [!IMPORTANT]  
> Image building is executed in **non-interactive** mode. Command-line interaction during compilation is not possible.  
> Therefore, when using `apt`, you must include the `-y` flag to ensure automatic confirmation.  
>  
> See [Dockerfile.base](.devcontainer/Dockerfile.base) for command examples.  

---

### Note on Automatic Environment Sourcing
During container creation, the following command is executed automatically:

```bash
echo 'source /workspace/ws/install/setup.bash' >> /home/mivia/.bashrc
```

This avoids the need to manually source the environment each time you run ROS2 nodes.  
However, if you create or change a workspace, this may cause issues. To disable this feature, modify the `postCreateCommand` key inside your target file:

* Windows/Mac: [devcontainer.json](.devcontainer/windows_mac/devcontainer.json)
* Linux: [devcontainer.json](.devcontainer/linux/devcontainer.json)

Example:
```json
"postCreateCommand": ""
```
Then rebuild the container.

---

# Building the Workspace
1. Open the container (see [Opening the Development Environment](#opening-the-development-environment)).
2. Navigate to the workspace directory:
```bash
cd ws
```
3. Build the workspace:
```bash
colcon build --symlink-install
```
4. Source the setup file:
```bash
source install/setup.bash
```

---

# Running the GUI

## X11

### Linux

1. On the host machine, open a shell and disable *Access Control*:
```bash
xhost +
```
2. Open the container and run:
```bash
xclock
```

### Windows
1. Install [Vcxsrv](https://vcxsrv.com/)
2. Run `XLaunch`
3. Set:
    1. `Multiple windows`
    2. `Display number`: -1
4. Press `Next`
5. Tick `Disable Access Control`
6. Open the container and run:
```bash
xclock
```

### macOS
1. Install [XQuartz](https://www.xquartz.org/)
2. Run `XQuartz`
3. Open settings/preferences
4. Allow network connections
5. Reboot the system
6. Reopen `XQuartz` via Launchpad
7. On the host machine, open a shell and disable *Access Control*:
```bash
xhost +
```
8. Open the container and run:
```bash
xclock
```

Reference: [http://mamykin.com/posts/running-x-apps-on-mac-with-docker/](http://mamykin.com/posts/running-x-apps-on-mac-with-docker/)

## RDP

1. Run [run_gui.bat](.devcontainer/windows_mac/run_gui.bat)

> [!NOTE]
> This works only for Windows. If you need to run it on macOS, reproduce the commands manually in your shell from the same directory.

> [!CAUTION]
> This will create a new container that will be removed on exit. Only changes made inside the `/workspace` directory will persist.

These commands will run the container as a daemon and start the RDP server on port `33890`.  
You can open the GUI using an RDP client such as Windows Remote Desktop with the following setting:
```
localhost:33890
```

> Username: `mivia`

> Password: `mivia`