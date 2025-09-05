#!/bin/bash
# Script de gestion wakdrop_backend

show_help() {
    echo "🎯 wakdrop_backend - Gestionnaire de Service"
    echo
    echo "Usage: ./wakdrop_backend.sh [COMMAND]"
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
        echo "🔧 Installation du service systemd wakdrop_backend..."
        
        # Vérifier qu'on est dans le bon répertoire
        if [ ! -f "wakdrop_backend.service" ]; then
            echo "❌ Erreur: fichier wakdrop_backend.service introuvable"
            echo "   Exécutez ce script depuis /opt/muppy/wakdrop_backendbackend"
            exit 1
        fi

        # Copier le fichier service
        echo "📝 Copie du fichier service..."
        sudo cp wakdrop_backend.service /etc/systemd/system/

        # Recharger systemd
        echo "🔄 Rechargement de systemd..."
        sudo systemctl daemon-reload

        # Activer le service (démarrage automatique)
        echo "✅ Activation du service..."
        sudo systemctl enable wakdrop_backend.service

        echo
        echo "🎉 Service wakdrop_backend installé avec succès !"
        echo
        echo "Commandes utiles:"
        echo "  ./wakdrop_backend.sh start        # Démarrer"
        echo "  ./wakdrop_backend.sh stop         # Arrêter"  
        echo "  ./wakdrop_backend.sh restart      # Redémarrer"
        echo "  ./wakdrop_backend.sh status       # Statut"
        echo "  ./wakdrop_backend.sh logs         # Logs en temps réel"
        echo
        echo "Le service démarrera automatiquement au boot du système."
        echo

        # Proposer de démarrer maintenant
        read -p "Voulez-vous démarrer le service maintenant ? [y/N] " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            echo "🚀 Démarrage du service..."
            sudo systemctl start wakdrop_backend
            sleep 2
            sudo systemctl status wakdrop_backend --no-pager
            echo
            echo "✅ Service démarré !"
            echo "🌐 API disponible sur: http://localhost:8000"
            echo "📚 Documentation: http://localhost:8000/docs"
        fi
        ;;
    start)
        echo "🚀 Démarrage de wakdrop_backend..."
        sudo systemctl start wakdrop_backend
        echo "✅ Service démarré"
        ;;
    stop)
        echo "⏹️ Arrêt de wakdrop_backend..."
        sudo systemctl stop wakdrop_backend
        echo "✅ Service arrêté"
        ;;
    restart)
        echo "🔄 Redémarrage de wakdrop_backend..."
        sudo systemctl restart wakdrop_backend
        echo "✅ Service redémarré"
        ;;
    status)
        echo "📊 Statut de wakdrop_backend:"
        sudo systemctl status wakdrop_backend --no-pager
        ;;
    logs)
        echo "📜 Logs wakdrop_backend (Ctrl+C pour quitter):"
        sudo journalctl -u wakdrop_backend -f
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
            echo "   Vérifiez que le service est démarré avec: ./wakdrop_backend.sh status"
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