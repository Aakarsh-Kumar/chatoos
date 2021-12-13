/*
 *
 *  Push Notifications codelab
 *  Copyright 2015 Google Inc. All rights reserved.
 *
 *  Licensed under the Apache License, Version 2.0 (the "License");
 *  you may not use this file except in compliance with the License.
 *  You may obtain a copy of the License at
 *
 *      https://www.apache.org/licenses/LICENSE-2.0
 *
 *  Unless required by applicable law or agreed to in writing, software
 *  distributed under the License is distributed on an "AS IS" BASIS,
 *  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 *  See the License for the specific language governing permissions and
 *  limitations under the License
 *
 */

/* eslint-env browser, serviceworker, es6 */

'use strict';

self.addEventListener('push', function(event) {
    console.log('[Service Worker] Push Received.');
    console.log(`[Service Worker] Push had this data: ${typeof event.data.text()}`);
    console.log(`[Service Worker] Push had this data: ${event.data.text().replace(/'/g, '"')}`);
    a = JSON.parse(event.data.text().replace(/'/g, '"'));

    const title = a.title;
    const options = {
        body: a.sender + ": " + a.body,
        icon: 'https://chatoos.herokuapp.com/static/img/logo-img.png',
        badge: 'https://static.turbosquid.com/Preview/001292/481/WV/_D.jpg',
        "vibrate": [400, 100, 400]
    };

    event.waitUntil(self.registration.showNotification(title, options));
});

self.addEventListener('notificationclick', function(event) {
    console.log('[Service Worker] Notification click Received.');

    event.notification.close();

    event.waitUntil(
        clients.openWindow(a.link)
    );
});