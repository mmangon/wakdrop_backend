#!/bin/bash
# Script de gestion WakDrop

show_help() {
    echo "🎯 WakDrop - Gestionnaire de Service"
    echo
    echo "Usage: ./wakdrop.sh [COMMAND]"
    echo
    echo "Commands:"
    echo "  install     Installer le service systemd"
    echo "  start       Démarrer le service"
    echo "  stop        Arrêter le service" 
    echo "  restart     Redémarrer le service"
    echo "  status      Afficher le statut"
    echo "  logs        Afficher les logs en temps réel"
    echo "  dev         Lancer en mode développement (terminal)"
    echo "  test        Tester l'API"
    echo "  help        Afficher cette aide"
}

case "$1" in
    install)
        echo "🔧 Installation du service systemd WakDrop..."
        
        # Vérifier qu'on est dans le bon répertoire
        if [ ! -f "wakdrop.service" ]; then
            echo "❌ Erreur: fichier wakdrop.service introuvable"
            echo "   Exécutez ce script depuis /opt/muppy/wakdropbackend"
            exit 1
        fi

        # Copier le fichier service
        echo "📝 Copie du fichier service..."
        sudo cp wakdrop.service /etc/systemd/system/

        # Recharger systemd
        echo "🔄 Rechargement de systemd..."
        sudo systemctl daemon-reload

        # Activer le service (démarrage automatique)
        echo "✅ Activation du service..."
        sudo systemctl enable wakdrop.service

        echo
        echo "🎉 Service WakDrop installé avec succès !"
        echo
        echo "Commandes utiles:"
        echo "  ./wakdrop.sh start        # Démarrer"
        echo "  ./wakdrop.sh stop         # Arrêter"  
        echo "  ./wakdrop.sh restart      # Redémarrer"
        echo "  ./wakdrop.sh status       # Statut"
        echo "  ./wakdrop.sh logs         # Logs en temps réel"
        echo
        echo "Le service démarrera automatiquement au boot du système."
        echo

        # Proposer de démarrer maintenant
        read -p "Voulez-vous démarrer le service maintenant ? [y/N] " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            echo "🚀 Démarrage du service..."
            sudo systemctl start wakdrop
            sleep 2
            sudo systemctl status wakdrop --no-pager
            echo
            echo "✅ Service démarré !"
            echo "🌐 API disponible sur: http://localhost:8000"
            echo "📚 Documentation: http://localhost:8000/docs"
        fi
        ;;
    start)
        echo "🚀 Démarrage de WakDrop..."
        sudo systemctl start wakdrop
        echo "✅ Service démarré"
        ;;
    stop)
        echo "⏹️ Arrêt de WakDrop..."
        sudo systemctl stop wakdrop
        echo "✅ Service arrêté"
        ;;
    restart)
        echo "🔄 Redémarrage de WakDrop..."
        sudo systemctl restart wakdrop
        echo "✅ Service redémarré"
        ;;
    status)
        echo "📊 Statut de WakDrop:"
        sudo systemctl status wakdrop --no-pager
        ;;
    logs)
        echo "📜 Logs WakDrop (Ctrl+C pour quitter):"
        sudo journalctl -u wakdrop -f
        ;;
    dev)
        echo "🔧 Mode développement - Lancement manuel..."
        source venv/bin/activate
        uvicorn main:app --host 0.0.0.0 --port 8000 --reload
        ;;
    test)
        echo "🧪 Test de l'API..."
        if curl -s http://localhost:8000/health > /dev/null; then
            echo "✅ API fonctionne - http://localhost:8000"
            echo "📚 Documentation: http://localhost:8000/docs"
        else
            echo "❌ API non accessible"
            echo "   Vérifiez que le service est démarré avec: ./wakdrop.sh status"
        fi
        ;;
    help|--help|-h|"")
        show_help
        ;;
    *)
        echo "❌ Commande inconnue: $1"
        echo
        show_help
        exit 1
        ;;
esac