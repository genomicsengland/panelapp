# -*- mode: ruby -*-
# vi: set ft=ruby :

Vagrant.configure("2") do |config|
  config.vm.box = "bento/ubuntu-16.04"
  config.vm.network "forwarded_port", guest: 8000, host: 9500, auto_correct: true
  config.vm.synced_folder ".", "/srv/panelappv2"
  config.vm.provider "virtualbox" do |vb|
    vb.memory = "2048"
  end
  # documentation for more information about their specific syntax and use.
  config.vm.provision "shell", inline: <<-SHELL
    sudo apt-get update
    sudo DEBIAN_FRONTEND=noninteractive apt-get -y -o Dpkg::Options::="--force-confdef" -o Dpkg::Options::="--force-confold" upgrade
    sudo apt-get install -y build-essential ntp python3.5 python3.5-dev python-pip python-virtualenv postgresql postgresql-contrib rabbitmq-server

    sudo -u postgres createuser -d panelapp
    sudo -u postgres createdb panelapp -O panelapp
    sudo -u postgres psql -d template1 -c "ALTER USER panelapp with encrypted password 'panelapp';"

    echo "export DATABASE_URL=postgres://panelapp:panelapp@localhost/panelapp" >> /home/vagrant/.bashrc
    echo "export DJANGO_SETTINGS_MODULE=panelapp.settings.dev" >> /home/vagrant/.bashrc
    echo "export DJANGO_LOG_LEVEL=DEBUG" >> /home/vagrant/.bashrc

    sudo -u vagrant virtualenv -p python3.5 /home/vagrant/.panelappv2
    sudo -H -u vagrant /home/vagrant/.panelappv2/bin/pip install setuptools==33.1.1
    sudo -H -u vagrant /home/vagrant/.panelappv2/bin/pip install -r /srv/panelappv2/deploy/dev.txt
    sudo -u vagrant DATABASE_URL=postgres://panelapp:panelapp@localhost/panelapp DJANGO_SETTINGS_MODULE=panelapp.settings.dev /home/vagrant/.panelappv2/bin/python /srv/panelappv2/panelapp/manage.py migrate

    echo "source /home/vagrant/.panelappv2/bin/activate" >> /home/vagrant/.bashrc
    echo "cd /srv/panelappv2/panelapp" >> /home/vagrant/.bashrc

    echo "To run the server run 'python manage.py runserver 0.0.0.0:8000' it will be available via http://localhost:9500/ on your host machine"
SHELL
end
