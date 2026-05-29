# Odoo 17 Pharmacy POS Management Dockerfile
FROM odoo:17.0
LABEL maintainer="Your Company <info@yourcompany.com>"

USER root
RUN pip3 install --upgrade pip && pip3 install arabic-reshaper python-bidi

USER odoo
COPY . /mnt/extra-addons/pharmacy_pos_management
