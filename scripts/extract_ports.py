import yaml
for p in ['socialNetwork/docker-compose.yml', 'hotelReservation/docker-compose.yml']:
    print(f'\n--- {p} ---')
    with open(p, encoding='utf-8') as f:
        data = yaml.safe_load(f)
    for svc, conf in data.get('services', {}).items():
        if 'ports' in conf:
            print(f'{svc}: {conf["ports"]}')
