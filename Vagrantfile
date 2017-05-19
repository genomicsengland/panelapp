# -*- mode: ruby -*-
# vi: set ft=ruby :

# All Vagrant configuration is done below. The "2" in Vagrant.configure
# configures the configuration version (we support older styles for
# backwards compatibility). Please don't change it unless you know what
# you're doing.
Vagrant.configure("2") do |config|
  # The most common configuration options are documented and commented below.
  # For a complete reference, please see the online documentation at
  # https://docs.vagrantup.com.

  # Every Vagrant development environment requires a box. You can search for
  # boxes at https://atlas.hashicorp.com/search.
  config.vm.box = "bento/ubuntu-16.04"

  # Disable automatic box update checking. If you disable this, then
  # boxes will only be checked for updates when the user runs
  # `vagrant box outdated`. This is not recommended.
  # config.vm.box_check_update = false

  # Create a forwarded port mapping which allows access to a specific port
  # within the machine from a port on the host machine. In the example below,
  # accessing "localhost:8080" will access port 80 on the guest machine.
  # NOTE: This will enable public access to the opened port
  config.vm.network "forwarded_port", guest: 8000, host: 9500

  # Create a forwarded port mapping which allows access to a specific port
  # within the machine from a port on the host machine and only allow access
  # via 127.0.0.1 to disable public access
  # config.vm.network "forwarded_port", guest: 80, host: 8080, host_ip: "127.0.0.1"

  # Create a private network, which allows host-only access to the machine
  # using a specific IP.
  # config.vm.network "private_network", ip: "192.168.33.10"

  # Create a public network, which generally matched to bridged network.
  # Bridged networks make the machine appear as another physical device on
  # your network.
  # config.vm.network "public_network"

  # Share an additional folder to the guest VM. The first argument is
  # the path on the host to the actual folder. The second argument is
  # the path on the guest to mount the folder. And the optional third
  # argument is a set of non-required options.
  config.vm.synced_folder ".", "/srv/panelappv2"

  # Provider-specific configuration so you can fine-tune various
  # backing providers for Vagrant. These expose provider-specific options.
  # Example for VirtualBox:
  #
  # config.vm.provider "virtualbox" do |vb|
  #   # Display the VirtualBox GUI when booting the machine
  #   vb.gui = true
  #
  #   # Customize the amount of memory on the VM:
  #   vb.memory = "1024"
  # end
  #
  # View the documentation for the provider you are using for more
  # information on available options.

  # Define a Vagrant Push strategy for pushing to Atlas. Other push strategies
  # such as FTP and Heroku are also available. See the documentation at
  # https://docs.vagrantup.com/v2/push/atlas.html for more information.
  # config.push.define "atlas" do |push|
  #   push.app = "YOUR_ATLAS_USERNAME/YOUR_APPLICATION_NAME"
  # end

  # Enable provisioning with a shell script. Additional provisioners such as
  # Puppet, Chef, Ansible, Salt, and Docker are also available. Please see the
  # documentation for more information about their specific syntax and use.
  config.vm.provision "shell", inline: <<-SHELL
    sudo apt-get update
    sudo apt-get upgrade -y
    sudo apt-get install -y build-essential python3.5 python3.5-dev python-pip python-virtualenv postgresql postgresql-contrib

    sudo -u postgres createuser -d panelapp
    sudo -u postgres createdb panelapp -O panelapp
    sudo -u postgres psql -d template1 -c "ALTER USER panelapp with encrypted password 'panelapp';"

    echo "export DATABASE_URL=postgres://panelapp:panelapp@localhost/panelapp" >> /home/vagrant/.bashrc
    echo "export DJANGO_SETTINGS_MODULE=panelapp.settings.dev" >> /home/vagrant/.bashrc

    sudo -u vagrant virtualenv -p python3.5 /home/vagrant/.panelappv2
    sudo -H -u vagrant /home/vagrant/.panelappv2/bin/pip install setuptools==33.1.1
    sudo -H -u vagrant /home/vagrant/.panelappv2/bin/pip install -r /srv/panelappv2/deploy/dev.txt
    sudo -u vagrant DATABASE_URL=postgres://panelapp:panelapp@localhost/panelapp DJANGO_SETTINGS_MODULE=panelapp.settings.dev /home/vagrant/.panelappv2/bin/python /srv/panelappv2/panelapp/manage.py migrate

    echo "source /home/vagrant/.panelappv2/bin/activate" >> /home/vagrant/.bashrc
    echo "cd /srv/panelappv2/panelapp" >> /home/vagrant/.bashrc

    echo "To run the server run 'python manage.py runserver 0.0.0.0:8000' it will be available via http://localhost:9500/ on your host machine"
SHELL
end
