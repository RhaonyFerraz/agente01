"""
Utilitário de Linha de Comando para Migração e Sincronização de Banco na Nuvem
Assistente Pessoal PWA -> Supabase / PostgreSQL / Neon

Uso:
  python cloud_sync.py --status              (Exibe status do banco atual)
  python cloud_sync.py --test <URL>          (Testa conexão com Supabase)
  python cloud_sync.py --migrate <URL>       (Aplica migrations no Supabase)
  python cloud_sync.py --export backup.json  (Exporta dados locais)
  python cloud_sync.py --import backup.json  (Importa dados)
"""

import os
import sys
import argparse
import json

if sys.platform == 'win32' and hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

try:
    import django
    django.setup()
except Exception as e:
    print(f"Erro ao inicializar Django: {e}")
    sys.exit(1)

from assistant.cloud_service import CloudDatabaseService
from django.core.management import call_command


def main():
    parser = argparse.ArgumentParser(description="Gerenciador de Nuvem de Dados (Supabase/PostgreSQL)")
    parser.add_argument('--status', action='store_true', help="Verifica status e latência do banco de dados")
    parser.add_argument('--test', type=str, help="Testa conexão com uma DATABASE_URL do PostgreSQL/Supabase")
    parser.add_argument('--migrate', type=str, nargs='?', const='env', help="Executa migrations no banco de dados da nuvem")
    parser.add_argument('--export', type=str, nargs='?', const='backup_assistente.json', help="Exporta dados para arquivo JSON")
    parser.add_argument('--import-file', type=str, help="Importa dados de um arquivo JSON")
    parser.add_argument('--set-url', type=str, help="Salva a DATABASE_URL no arquivo .env")

    args = parser.parse_args()

    if args.status:
        st = CloudDatabaseService.get_status()
        print("\n" + "="*50)
        print("📊 STATUS DO BANCO DE DADOS ATIVO")
        print("="*50)
        print(f" Provedor:        {st['provider']}")
        print(f" Motor/Vendor:    {st['vendor']}")
        print(f" Host:            {st['host']}")
        print(f" Conectado:       {'✅ Sim' if st['is_connected'] else '❌ Não'}")
        if st['latency_ms'] is not None:
            print(f" Latência:        {st['latency_ms']} ms")
        print(f" Total Registros: {st['total_records']}")
        print(f" Detalhes:        {st['counts']}")
        print("="*50 + "\n")

    elif args.test:
        print(f"\n⚡ Testando conexão com: {args.test[:35]}...")
        res = CloudDatabaseService.test_connection_string(args.test)
        if res.get("success"):
            print(f"✅ {res['message']}")
            print(f"Versão PostgreSQL: {res.get('version')}")
        else:
            print(f"❌ Erro na conexão: {res.get('error')}")

    elif args.set_url:
        CloudDatabaseService.save_cloud_url_to_env(args.set_url)
        print(f"✅ DATABASE_URL salva no .env com sucesso!")
        print("Reinicie o servidor Django para ativar a conexão com a nuvem.")

    elif args.export:
        filepath = args.export
        data = CloudDatabaseService.export_data_bundle()
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        print(f"✅ Dados exportados com sucesso para: {filepath}")
        print(f"Eventos: {len(data['events'])}, Tarefas: {len(data['tasks'])}, E-mails: {len(data['emails'])}, Mensagens: {len(data['messages'])}")

    elif args.import_file:
        if not os.path.exists(args.import_file):
            print(f"❌ Arquivo não encontrado: {args.import_file}")
            return
        with open(args.import_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        counts = CloudDatabaseService.import_data_bundle(data)
        print(f"✅ Importação concluída! Registros importados: {counts}")

    else:
        parser.print_help()


if __name__ == '__main__':
    main()
