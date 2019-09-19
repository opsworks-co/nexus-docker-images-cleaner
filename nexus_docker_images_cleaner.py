from requests import get, delete
from datetime import date, timedelta, datetime
from json import loads
from os import environ
from argparse import ArgumentParser


# main class
class NexusCleaner:

    # init from env var
    # refactor this later (get rid of if)
    def __init__(self):
        self.ChkKeep_fl = 0
        self.ChkDays_fl = 0
        self.NEXUS_ADDRESS = environ.get('NEXUS_ADDRESS')
        self.NEXUS_PORT = environ.get('NEXUS_PORT')
        self.NEXUS_USER_LOGIN = environ.get('NEXUS_USER_LOGIN')
        self.NEXUS_USER_PASSWORD = environ.get('NEXUS_USER_PASSWORD')
        if (self.NEXUS_ADDRESS is None or
                self.NEXUS_PORT is None or
                self.NEXUS_USER_LOGIN is None or
                self.NEXUS_USER_PASSWORD is None):
            print('Environment variables not set')
            raise SystemExit

    # find all docker images by repo, name, tag
    # creating and appending my_images
    def _check_nexus_images(self, RepoName='', ImageName='', ImageVersion=''):
        params = {'format': 'docker'}
        if RepoName:
            params['repository'] = RepoName
        if ImageName:
            params['name'] = ImageName
        if ImageVersion:
            params['version'] = ImageVersion
        search_url = 'http://{0}:{1}/service/rest/v1/search'.format(
            self.NEXUS_ADDRESS,
            self.NEXUS_PORT)

        cToken = 1
        iParms = params
        self.my_images = []

        while cToken is not None:
            try:
                response = get(search_url, auth=(
                    self.NEXUS_USER_LOGIN,
                    self.NEXUS_USER_PASSWORD),
                               params=iParms)
            except Exception as error:
                print('Problem with connect to Nexus:')
                print(error)
                raise SystemExit
            try:
                response = response.json()
            except Exception as error:
                print('Problem with json response from Nexus:')
                print(error)
                raise SystemExit

            if "continuationToken" in response:
                dToken = {"continuationToken": response["continuationToken"]}
                cToken = dToken['continuationToken']
                iParms['continuationToken'] = cToken

            images = response['items']

            for image in images:
                # very strange REST record - need investigate
                try:
                    ImageUrl = image['assets'][0]['downloadUrl']
                except:
                    continue

                response = get(ImageUrl, auth=(
                    self.NEXUS_USER_LOGIN,
                    self.NEXUS_USER_PASSWORD))

                response = response.json()
                tmp_str = response['history'][0]['v1Compatibility']
                tmp_json = loads(tmp_str)
                CreateDate = tmp_json['created']
                ImageSha = image['assets'][0]['checksum']['sha256']
                RepoName = image['repository']
                ImageName = image['name']
                ImageVersion = image['version']

                self.my_images.append({
                    'ImageUrl': ImageUrl,
                    'CreateDate': CreateDate,
                    'ImageSha': ImageSha,
                    'RepoName': RepoName,
                    'ImageName': ImageName,
                    'ImageVersion': ImageVersion,
                })
                print('.', end='', flush=True)

            print(len(self.my_images))

        return len(self.my_images)

    # find all docker images by repo, name
    # creating and appending all_image_names_list
    def _get_all_image_names(self, RepoName=''):
        print('Repository discovery...')
        params = {'format': 'docker'}
        if RepoName: params['repository'] = RepoName
        search_url = 'http://{0}:{1}/service/rest/v1/search'.format(self.NEXUS_ADDRESS, self.NEXUS_PORT)

        cToken = 1
        iParms = params
        self.all_image_names_list = []
        ain_flist = []

        while cToken is not None:
            try:
                response = get(search_url, auth=(
                    self.NEXUS_USER_LOGIN,
                    self.NEXUS_USER_PASSWORD),
                               params=iParms)
            except Exception as error:
                print('Problem with connect to Nexus:')
                print(error)
                raise SystemExit
            try:
                response = response.json()
            except Exception as error:
                print('Problem with json response from Nexus:')
                print(error)
                raise SystemExit

            if "continuationToken" in response:
                dToken = {"continuationToken": response["continuationToken"]}
                cToken = dToken['continuationToken']
                iParms['continuationToken'] = cToken

            images = response['items']
            for image in images:
                ImageName = image['name']
                ain_flist.append(ImageName)
                print('.', end='', flush=True)

        for i in ain_flist:
            if i not in self.all_image_names_list:
                self.all_image_names_list.append(i)

        print('.')
        # print(self.all_image_names_list)  # GCh for debug

    # prepare my_images to delete without keep images
    def _check_image_keep(self, Keep):

        # check this bug(?)
        if Keep < 0:
            print('Incorrect type')
            raise SystemExit

        if Keep <= len(self.my_images):
            self.my_images = sorted(
                self.my_images,
                key=lambda elem: elem['CreateDate'],
                reverse=True)
            self.my_images = self.my_images[Keep:]
            self.del_images = self.my_images
        elif Keep > len(self.my_images):
            print('All images keeps')
            raise SystemExit

    # prepare del_images to usage without fresh images
    def _check_image_date(self, Days):
        OldDate = date.today() - timedelta(days=Days)
        for image in self.my_images:
            ImageDate = image['CreateDate'][:10]
            ImageDate = datetime.strptime(ImageDate, "%Y-%m-%d").date()
            if ImageDate < OldDate:
                self.del_images.append(image)

    # del image by url
    # return request status code
    def _delete_image(self, ImageUrl, ImageSha):
        digest = 'sha256:' + ImageSha
        headers = {
            'Accept': 'application/vnd.docker.distribution.manifest.v2+json'}
        tmp_pos = ImageUrl.rfind('/')
        DelUrl = ImageUrl[:tmp_pos + 1] + digest
        try:
            response = delete(DelUrl, auth=(  # GCh for debug: delete() -> get()
                self.NEXUS_USER_LOGIN,
                self.NEXUS_USER_PASSWORD),
                           headers=headers)
        except:
            print('Problem with Nexus server')
            raise SystemExit

        return response.status_code

    # clean all old images (by day, by repo, by image name, by tag)
    # return list of dicts of deleted images
    def clean_old_images(
            self,
            Keep=0,
            Days=0,
            RepoName='',
            ImageName='',
            ImageVersion=''):

        imgs_n=self._check_nexus_images(
            RepoName=RepoName,
            ImageName=ImageName,
            ImageVersion=ImageVersion)

        self.del_images = []

        if ( self.ChkKeep_fl and Keep <= imgs_n ):
            self._check_image_keep(Keep)
        if ( self.ChkDays_fl ):
            self._check_image_date(Days)

        if ( len(self.del_images) > 0 ):
            for image in self.del_images:
                if (Keep > 0):
                    if (image['ImageVersion'] != 'latest'):
                        image['DeleteCode'] = self._delete_image(
                            image['ImageUrl'],
                            image['ImageSha'])
                        print(('REPOSITORY: {0} | DELETED: {1}:{2}  | {3}'.format(
                            image['RepoName'],
                            image['ImageName'],
                            image['ImageVersion'],
                            image['CreateDate'])))
                else:
                    image['DeleteCode'] = self._delete_image(
                        image['ImageUrl'],
                        image['ImageSha'])
                    print(('REPOSITORY: {0} | DELETED: {1}:{2}  | {3}'.format(
                        image['RepoName'],
                        image['ImageName'],
                        image['ImageVersion'],
                        image['CreateDate'])))

        if (self.del_images is None):
            print('No images in delete query')

        return self.del_images

# main function
def main():
    def flag_parser():
        # my parser check
        def simple_parser_check(my_args_dict):
            def parser_cjeck_error_raiser():
                print('''Significant errors in ArgumentParser
                     - contact the maintainer.''')
                raise SystemExit

            if (my_args_dict['i'] == '' and
                    my_args_dict['all_images'] == False):
                parser_cjeck_error_raiser()
            elif (my_args_dict['r'] == '' and
                  my_args_dict['all-repositories'] == False):
                parser_cjeck_error_raiser()

        # create parser
        nexus_cleaner_parser = ArgumentParser(
            prog='python3 nexus_docker_images_cleaner.py',
            description='''Delete docker images in Nexus Repository Manager 3
                Requires environment variables:
                    NEXUS_ADDRESS, 
                    NEXUS_PORT, 
                    NEXUS_USER_LOGIN, 
                    NEXUS_USER_PASSWORD.
                ''')

        # create repo group flags
        repos_group = nexus_cleaner_parser.add_mutually_exclusive_group(
            required=True)
        repos_group.add_argument(
            '-r',
            metavar='str_repo_name',
            type=str,
            default='',
            help='''Repository name. 
                If you want to work with all repositories 
                use '--all-repositories' option.''')
        repos_group.add_argument(
            '--all-repositories',
            action='store_true',
            help="Use to clean all repositories instead '-r'.")

        # create image group flags
        images_group = nexus_cleaner_parser.add_mutually_exclusive_group(
            required=True)
        images_group.add_argument(
            '-i',
            metavar='str_image_name',
            type=str,
            default='',
            help='''Image name. 
                If you want to work with all images use '--all-images' option.''')
        images_group.add_argument(
            '--all-images',
            action='store_true',
            help="Use to clean all images instead '-i'.")

        # create keep and day group flags
        keep_day_group = nexus_cleaner_parser.add_mutually_exclusive_group()
        keep_day_group.add_argument(
            '-d',
            # default=10,
            metavar='int_days',
            type=int,
            help='''Days count after which image is deleted (10 by default). 
                (!) Can't be used with '-k' option.''')
        keep_day_group.add_argument(
            '-k',
            # default=5,
            metavar='int_keep',
            type=int,
            help='''Number of latest images to keep (5 by default). 
                (!) Can't be used with '-d' option.''')

        # create version flag
        nexus_cleaner_parser.add_argument(
            '-t',
            metavar='str_image_version',
            default='',
            type=str,
            help="[str] Tag name (delete all by default).")

        my_args_dict = vars(nexus_cleaner_parser.parse_args())
        simple_parser_check(my_args_dict)
        return my_args_dict

    nexus = NexusCleaner()

    my_args_dict = flag_parser()
    Keep_num=my_args_dict['k']
    Days_num=my_args_dict['d']
    nexus.ChkKeep_fl=0
    nexus.ChkDays_fl=0
    if ( Keep_num is not None and Keep_num >= 0 ):
        Days_num=0
        nexus.ChkKeep_fl=1
    elif ( Days_num is not None and Days_num >= 0 ):
        Keep_num=0
        nexus.ChkDays_fl=1
    if ( Keep_num is None and Days_num is None):
        Keep_num=5
        Days_num=0
        nexus.ChkKeep_fl=1
    if ( Keep_num is not None and Keep_num < 0 ):
        print('The argument -k <keep> is negative')
        raise SystemExit
    elif ( Days_num is not None and  Days_num < 0 ):
        print('The argument -d <days> is negative')
        raise SystemExit

    Keep = Keep_num
    Days = Days_num
    RepoName = my_args_dict['r']
    ImageName = my_args_dict['i']
    ImageVersion = my_args_dict['t']

    if ImageName == '':
        nexus._get_all_image_names(RepoName=RepoName)
        for imgname_i in nexus.all_image_names_list:
            print(('[{0}]'.format(imgname_i)))
            nexus.clean_old_images(
                Keep=Keep,
                Days=Days,
                RepoName=RepoName,
                ImageName=imgname_i,
                ImageVersion=ImageVersion)
    else:
        nexus.clean_old_images(
            Keep=Keep,
            Days=Days,
            RepoName=RepoName,
            ImageName=ImageName,
            ImageVersion=ImageVersion)

if __name__ == "__main__":
    main()
