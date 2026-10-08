"""Read public alternative schemas and probe public access; never forward PitchAPI credentials."""
import json
from pathlib import Path

import httpx

from scout.pitchapi import write

root = Path('data/pitchapi/alternatives-20261006')
report = {'activated': False, 'requests': []}
with httpx.Client(timeout=25, follow_redirects=False) as client:
    for url in ['https://football-api.yuvron.online/openapi.json',
                'https://football-api.yuvron.online/v1/competitions',
                'https://football-api.yuvron.online/v1/premier-league/players?season=2025-26&limit=2']:
        try:
            response = client.get(url)
            entry = {'url': url, 'status': response.status_code}
            if response.status_code == 200 and len(response.content) < 5_000_000:
                document = response.json()
                if 'openapi' in document:
                    write(root / 'yuvron-openapi.json', document)
                    entry['servers'] = document.get('servers', [])
                    path = document['paths']['/{competition}/players/{id}']
                    schema = path['get']['responses']['200']['content']['application/json']['schema']
                    entry['player_schema'] = schema
                else:
                    write(root / ('public-' + str(len(report['requests'])) + '.json'), document)
                    entry['keys'] = sorted(document) if isinstance(document, dict) else []
            report['requests'].append(entry)
        except (httpx.HTTPError, ValueError, KeyError, TypeError) as error:
            report['requests'].append({'url': url, 'failure': type(error).__name__})
write(root / 'access-report.json', report)
print(json.dumps({'activated': False, 'requests': [{k: v for k, v in row.items() if k != 'player_schema'}
                                               for row in report['requests']]}, indent=2))
