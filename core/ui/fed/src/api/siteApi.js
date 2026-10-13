import request, { API_VERSION_PREFIX } from 'service/request';

const API_SITE = `${API_VERSION_PREFIX}/setup/site`;

function readUrls(json) {
  const message = json?.message || {};
  const docs = message.docs && typeof message.docs === 'object' ? message.docs : {};
  return {
    disclaimerUrl: String(message.disclaimer_url || ''),
    licenseUrl: String(message.license_url || ''),
    contactUrl: String(message.contact_url || ''),
    registerUrl: String(message.register_url || ''),
    docs: {
      strategy: String(docs.strategy || ''),
      opportunities: String(docs.opportunities || ''),
      tag: String(docs.tag || ''),
      datasource: String(docs.datasource || ''),
      contract: String(docs.contract || ''),
    },
  };
}

export function fetchSiteUrls() {
  return request.getJson(API_SITE).then(readUrls);
}
