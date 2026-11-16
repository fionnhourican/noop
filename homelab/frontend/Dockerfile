FROM nginx:alpine

# Remove default nginx configs
RUN rm /etc/nginx/conf.d/default.conf

# Copy custom reverse proxy config and static files
COPY nginx.conf /etc/nginx/nginx.conf
COPY index.html /usr/share/nginx/html/index.html

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
