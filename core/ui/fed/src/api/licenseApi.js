import request, { API_VERSION_PREFIX } from 'service/request';

const API_LICENSE = `${API_VERSION_PREFIX}/setup/license`;

function readPayload(json) {
  const message = json?.message || {};
  return {
    accepted: Boolean(message.accepted),
    revision: String(message.revision || ''),
    disclaimerUrl: String(message.disclaimer_url || ''),
    licenseUrl: String(message.license_url || ''),
    exiting: Boolean(message.exiting),
  };
}

export function fetchLicenseAcceptance() {
  return request.getJson(API_LICENSE).then(readPayload);
}

export function acceptLicense() {
  return request.postJson(`${API_LICENSE}/accept`, { body: {} }).then(readPayload);
}

export function declineLicense() {
  return request.postJson(`${API_LICENSE}/decline`, { body: {} }).then(readPayload);
}
