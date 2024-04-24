FROM node AS builder
WORKDIR /dummy
COPY package.json .
RUN npm install
COPY . .
RUN npm run build

FROM nginx AS runtime
COPY --from=builder /dummy/build /usr/share/nginx/html/
RUN rm /etc/nginx/conf.d/default.conf
COPY nginx.conf /etc/nginx/conf.d
CMD [ "nginx", "-g", "daemon off;" ]
