# Description

This scripts deletes docker images in Nexus Repository Manager 3.

## Usage

### Prerequisites
python3

### Environmental variables
```
NEXUS_ADDRESS
NEXUS_PORT
NEXUS_USER_LOGIN
NEXUS_USER_PASSWORD
```

### Arguments
-   `-h, --help`           show this help message and exit
-   `-r str_repo_name`     Repository name. If you want to work with all repositories use '--all-repositories' option
-   `--all-repositories`   Use to clean all repositories instead '-r'
-   `-i str_image_name`    Image name. If you want to work with all images use '--all-images' option.
-   `--all-images`         Use to clean all images instead '-i'.
-   `-d int_days`          Days count after which image is deleted (10 by default). (!) **Can't be used with '-k' option**.
-  `-k int_keep`           Number of latest images to keep (5 by default). (!) **Can't be used with '-d' option**.
-  `-t str_image_version`  [str] Tag name (delete all by default).

### How to run
```
python3 nexus_docker_images_cleaner.py [-h] 
                                       (-r str_repo_name | --all-repositories)
                                       (-i str_image_name | --all-images)
                                       [-d int_days | -k int_keep]
                                       [-t str_image_version]
```

### Examples

To clean all images from `registry` repository except one latest:
```
python3 nexus_docker_images_cleaner.py -r registry --all-images -k 1
```
To clean images with tag `smth_tag` from `repo_name` repository older than 7 days:
```
python3 nexus_docker_images_cleaner.py -r repo_name -i smth_image_name -d 7 -t smth_tag
```

#### Bash script
```
#!/bin/bash

export NEXUS_ADDRESS="nexus3.local"
export NEXUS_PORT="80"
export NEXUS_USER_LOGIN="user"
export NEXUS_USER_PASSWORD="passwd"

python3 nexus_docker_images_cleaner.py -r smth_repo_name -i smth_image_name -d 7 -t smth_tag
```
