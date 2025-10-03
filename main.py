import requests
import logging
import os
import json
from datetime import datetime, timezone
from dateutil import parser as date_parser
import sqlite3
from pathlib import Path
import argparse

log_levels = {
    'DEBUG': logging.DEBUG,
    'INFO': logging.INFO,
    'WARNING': logging.WARNING,
    'ERROR': logging.ERROR,
    'CRITICAL': logging.CRITICAL
}

log_level = log_levels[os.environ.get('LOG_LEVEL', 'INFO')]
logging.basicConfig(level=log_level, format='%(asctime)s [kuma-asset-archiver] %(levelname)s %(message)s')

requests.packages.urllib3.disable_warnings(requests.packages.urllib3.exceptions.InsecureRequestWarning)


class Kuma:
    
    def __init__(self):
        
        self.api_version = '/api/v3'
        self.verifiy = False
        self.limit = 250
        self.OK =  'OK'
        self.ERROR = 'ERROR'

    def _make_request(self, method, url, params=None, data=None):
        
        result = {
                    "status": None,
                    "details": None
                  }
        try:
            r = requests.request(method=method, url=url, params=params, data=data, verify=self.verifiy, headers=self.headers)
            if r.status_code == 200 or r.status_code == 204:
                result['status'] = self.OK
                result['details'] = None
            else:
                result['status'] = self.ERROR
                result['details'] = f"Status code: {r.status_code}. Details: {r.text}"
        
        except Exception as e:
            result['status'] = self.ERROR
            result['details'] = str(e)
        
        finally:
            return result, r
           
    def connect(self, address, port, token):
        
        self.address = address
        self.port = port
        self.token = token
        self.headers = {"Authorization" : "Bearer " + self.token}
        self.base_url = 'https://' + self.address + ':' + self.port + self.api_version
        self.whoami_url = self.base_url + '/users/whoami'

        method = 'get'
        result, r = self._make_request(method=method, url=self.whoami_url)

        return result

    def get_tenants(self):

        tenants = []
        page = 1
        count = self.limit
        
        method = 'get'
        tenants_url = self.base_url + "/tenants"
        params = {}

        while count == self.limit:
            params['page'] = page
            result, r = self._make_request(method=method, url=tenants_url, params=params)
            
            if result['status'] == self.OK:
                tenants_batch = r.json()
                for t in tenants_batch:
                    tenants.append(
                        (t['name'], t['id'])
                    )
                count = len(tenants_batch)
                page = page + 1
            
            else:
                count = 0
        
        return result, tenants

    def get_assets(self, page: int = None, id=None, tenantID=None, name=None, fqdn=None, ip=None, mac=None):
        
        assets = []
        page = 1
        count = self.limit
        
        asset_url = self.base_url + "/assets"
        method = "get"

        params = {
            "page": page,
            "id": id,
            "tenantID": tenantID,
            "name": name,
            "fqdn": fqdn,
            "ip": ip,
            "mac": mac    
        }

        while count == self.limit:
            params['page'] = page
            result, r = self._make_request(method=method, url=asset_url, params=params)
            
            if result['status'] == self.OK:
                tenants_batch = r.json()
                for t in tenants_batch:
                    assets.append(t)
                count = len(tenants_batch)
                page = page + 1
            
            else:
                count = 0        

        result, r =  self._make_request(method=method, url=asset_url, data=json.dumps(params))
    
        return result, assets
    
    def import_assets(self, assets, tenant_id):

        assets_url = self.base_url + "/assets/import"
        
        params = {
            "assets": assets,
            "tenantID": tenant_id
        }
        method='post'

        print(params)
        result, r = self._make_request(method=method, url=assets_url, data=json.dumps(params))

        return result



def main():

    parser = argparse.ArgumentParser(description="kuma assets archiver")
    parser.add_argument("--address", type=str, help="kuma core ip/fqdn")
    parser.add_argument("--port", type=str, default="7223", help="kuma public api port")
    parser.add_argument("--token", type=str, help="api token")
    parser.add_argument("--days_to_archive", type=int, default=30, help="days to archive")
    parser.add_argument("--db", type=str, default="/opt/kaspersky/kuma/core/00000000-0000-0000-0000-000000000000/raft/sm/db", help="kuma sqlite db")
    args = parser.parse_args()

    address = args.address
    port = args.port
    token = args.token
    days_to_archive = args.days_to_archive
    assets_to_archive = []
    now = datetime.now(timezone.utc)
    db_file = Path(args.db)

    logging.info(f"Script arguments: {address, port, token, days_to_archive, db_file}")

    logging.info(f"Archiver is setted to {days_to_archive} days")
    
    kuma = Kuma()
    
    result = kuma.connect(address, port, token)
    if result['status'] == kuma.OK:
        logging.info(f"Success, connection details: {result['details']}")
    else:
        logging.error(f"Connection canceled, reason: {result['details']}")

    assets_request = kuma.get_assets()

    if result['status'] == kuma.OK:
        assets = assets_request[1]
        logging.info(f"Success {len(assets)} asset(s) fetched")
    else:
        logging.error(f"Connection canceled, reason: {result['details']}")

    for asset in assets:
        if (now - date_parser.isoparse(asset["updated"])).days >= days_to_archive and asset["archived"] == False:
            asset.update({"archived":True})
            assets_to_archive.append(asset["id"])
    
    
    logging.info(f"Asset(s) to archive: {len(assets_to_archive)}")

    MAX_VARS = 999

    def chunked(iterable, size):
        for i in range(0, len(iterable), size):
            yield iterable[i:i + size]

    try:
        con = sqlite3.connect(str(db_file))
        cur = con.cursor()

        for chunk in chunked(assets_to_archive, MAX_VARS):
            placeholders = ",".join("?" * len(chunk))
            query = f"UPDATE assets SET archived = 1 WHERE id IN ({placeholders})"
            res = cur.execute(query, chunk)

        con.commit()
        logging.info(f"Asset(s) updated: {len(assets_to_archive)}")
        logging.info("Done!")

    except sqlite3.Error as e:
        logging.error(f"SQLite error: {e}")

    except Exception as e:
        logging.error(f"Unexpected error: {e}")

    finally:
        if cur:
            cur.close()
        if con:
            con.close()



if __name__ == "__main__":
    main()