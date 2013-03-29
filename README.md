VideoPI
=======

A web-based remote controller for Raspberry focused on the online video service.

## 硬件

* 首先是RaspberryPI了，我选的是Model B，否则还得自己买网卡。
* 有MicroUSB口的电源，5V，虽然Model B官方是700ma就可以了，但是实际上最好是能更高一点。我用700ma的电源，网络在起来几分钟后就会自动断开。电源最好是好点的
* 容量大于等于4G的SD卡一张，注意**不是**MicroSD卡。
* 路由器一个（要能支持有线，因为Model B自带的是有线网卡）。
* HDMI口的显示器或者电视。
* HDMI线一条。
* 一台能读写SD卡的电脑。

## 安装Archlinux系统

* 从http://www.raspberrypi.org/downloads下载Archlinux ARM的img，下载的是一个zip包，解压缩后就是个img文件。
* 将img文件load到卡上。参考[这里](http://elinux.org/RPi_Easy_SD_Card_Setup)，如果你是第一次burn img文件的话。对于使用Mac内置读卡器的人，建议使用[RPi-sd card builder](http://alltheware.wordpress.com/2012/12/11/easiest-way-sd-card-setup/)，直接用dd命令可能会失败。
* 将卡插到板子上，接好显示器或者电视，接通电源。
* 顺利的话应该能看到一个彩色的屏，然后就会进入Archlinux，10秒左右启动完毕。
* Archlinux的网卡默认是dhcp的，ssh服务会自动启动。
* 登录到路由器的管理界面，看看获得的ip是多少。如果有键盘的话，直接`ip addr`看就可以了。如果路由器有静态dhcp功能的话，可以在路由器上设置一下固定ip，不行就在Archlinux里面设置静态ip了（[相关链接](https://wiki.archlinux.org/index.php/Network_Configuration#Static_IP_address)）。
* 是时候通过ssh远程登录到系统了，默认用户名和密码是`root/root`。

## 升级系统以及固件

非常简单，和普通机器上的Archlinux一样，执行下面的命令：

`pacman -Syu`

时间比较长，等待的过程中可以继续下面的步骤。

## 安装omxplayer

* omxplayer的包在AUR里面，猛击[这里](https://aur.archlinux.org/packages/omxplayer-git/)可以看到相关介绍。
* 创建一个新的用户，用于makepkg，根据个人喜好选择<username>

  ```bash
  useradd <username>
  mkdir /home/<username>
  chown <username> /home/<username>
  ```

* 切换到刚创建的用户，下载omxplayer的build文件。

  `wget https://aur.archlinux.org/packages/om/omxplayer-git/omxplayer-git.tar.gz`

* 在安装omxplayer之前，先安装一下预先需要的软件包（root用户）。

  `pacman -S git fakeroot gcc make patch fbset ffmpeg ffmpeg-compat freetype2 pcre rtmpdump boost`
  
* 上一步完成后就可以准备build了，切换到新创建的用户，解压缩下载的文件

  ```bash
  tar zxvf omxplayer-git.tar.gz
  cd omxplayer-git
  makepkg
  ```

* makepkg的时间会比较长，耐心等候，结束后就可以安装omxplayer了（root用户）

  `pacman -U *.pkg.tar.xz`


## 安装VideoPI

VideoPI是基于bottlepy以及jquerymobile的一个RB的遥控器，可以在电脑、智能手机以及平板电脑上使用。Repo在[这里](https://github.com/bladeworks/VideoPI)。下面是安装步骤。

* 安装预先需要的软件包（root用户）
   
  ```bash
  pacman -S python2 fbv
  ln -s /usr/bin/python2 /usr/bin/python
  cd /tmp
  wget https://pypi.python.org/packages/2.7/s/setuptools/setuptools-0.6c11-py2.7.egg#md5=fe1f997bc722265116870bc7919059ea
  sh setuptools-0.6c11-py2.7.egg
  wget https://pypi.python.org/packages/source/p/pip/pip-1.3.1.tar.gz#md5=cbb27a191cebc58997c4da8513863153
  tar zxvf pip-1.3.1.tar.gz
  cd pip-1.3.1
  python setup.py install
  pip install bottle
  pip install pexpect
  ```
  
* 如果要看Youtube，还需要youtube-dl（root用户）。
  
  ```bash
  wget http://youtube-dl.org/downloads/2013.02.25/youtube-dl -O /usr/local/bin/youtube-dl
  chmod a+x /usr/local/bin/youtube-dl
  ```
  
* 安装VideoPI（root用户）

  ```bash
  cd /root
  git clone https://github.com/bladeworks/VideoPI
  cd VideoPI
  sh install_service.sh
  chmod +x start.sh
  sync
  reboot
  ```

## 使用VideoPI

* 使用电脑或智能手机或平板电脑打开网址：`http://<raspberry pi ip>`就可以看到控制界面了。
* 点击Browse可以选择腾讯视频，优酷以及Youtube。
* 在相应网站找到视频后点击机会在RB中播放。