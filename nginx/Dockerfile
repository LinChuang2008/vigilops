FROM nginx:alpine
# envsubst for variable substitution in config
RUN apk add --no-cache gettext
COPY ssl.conf /etc/nginx/templates/default.conf.template
EXPOSE 80 443
