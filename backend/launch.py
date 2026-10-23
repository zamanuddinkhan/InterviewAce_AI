"""CMD-friendly startup with a readable duplicate-server check."""
import argparse
import json
import socket
from urllib.request import urlopen


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--port',type=int,default=8000)
    args=parser.parse_args()
    if not 1 <= args.port <= 65535:parser.error('Port must be between 1 and 65535.')
    address=f'http://127.0.0.1:{args.port}'
    with socket.socket() as probe:
        occupied=probe.connect_ex(('127.0.0.1',args.port))==0
    if occupied:
        try:
            with urlopen(address+'/api/health',timeout=3) as response:
                health=json.load(response)
            if health.get('ai_mode')=='local Ollama':
                print(f'InterviewAce is already running: {address}')
                print('Open that URL. To load changed .env settings, stop its CMD window with Ctrl+C first.')
                return
        except Exception:pass
        raise SystemExit(f'Port {args.port} is occupied. Stop the other server, or use run.cmd --port 8001.')
    from .local_mysql import ensure_running
    ensure_running()
    import uvicorn
    uvicorn.run('backend.app.main:app',host='127.0.0.1',port=args.port,workers=1,ws_max_size=32768)


if __name__=='__main__':main()
