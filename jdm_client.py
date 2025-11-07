"""
Client pour interagir avec l'API JDM (Jeux De Mots)
"""
import requests
import json
import time
import os
import logging
from typing import List, Dict, Any, Optional, Union

class JDMCache:
    """
    Cache pour stocker les résultats des requêtes à l'API JeuxDeMots
    afin de réduire le nombre d'appels réseau et d'améliorer les performances.
    """
    def __init__(self, cache_dir: str = "data/cache", max_age: int = 86400, logging: bool = True):
        """
        Initialise le cache JDM
        
        Args:
            cache_dir: Répertoire où stocker les fichiers de cache
            max_age: Durée de validité maximale des entrées du cache en secondes (par défaut: 1 jour)
        """
        self.memory_cache = {}  # Cache en mémoire pour les accès rapides
        self.cache_dir = cache_dir
        self.max_age = max_age
        self.logging = logging
        
        # Créer le répertoire de cache s'il n'existe pas
        os.makedirs(cache_dir, exist_ok=True)
    
    def _get_cache_key(self, method: str, **params) -> str:
        """
        Génère une clé de cache unique basée sur la méthode et les paramètres
        
        Args:
            method: Nom de la méthode d'API (ex: "get_relations_from")
            params: Paramètres de la requête
        
        Returns:
            Clé de cache unique
        """
        # Convertir les paramètres en chaîne triée pour garantir l'unicité
        param_str = json.dumps(params, sort_keys=True)
        return f"{method}_{param_str}"
    
    def _get_cache_file_path(self, key: str) -> str:
        """
        Obtient le chemin du fichier cache pour une clé donnée
        
        Args:
            key: Clé de cache
        
        Returns:
            Chemin du fichier cache
        """
        # Utiliser un hash de la clé pour éviter les problèmes de noms de fichiers
        import hashlib
        hashed_key = hashlib.md5(key.encode()).hexdigest()
        return os.path.join(self.cache_dir, f"{hashed_key}.json")
    
    def get(self, method: str, **params) -> Optional[Dict]:
        """
        Récupère un résultat du cache s'il existe et n'est pas expiré
        
        Args:
            method: Nom de la méthode d'API
            params: Paramètres de la requête
        
        Returns:
            Résultat mis en cache ou None si pas de cache ou expiré
        """
        key = self._get_cache_key(method, **params)
        
        # Vérifier d'abord le cache en mémoire
        if key in self.memory_cache:
            cache_entry = self.memory_cache[key]
            if time.time() - cache_entry["timestamp"] < self.max_age:
                if self.logging: 
                    print(f"[CACHE-MEM] Hit pour {method}")
                return cache_entry["data"]
        
        # Ensuite vérifier le cache sur disque
        file_path = self._get_cache_file_path(key)
        if os.path.exists(file_path):
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    cache_entry = json.load(f)
                
                # Vérifier si l'entrée est expirée
                if time.time() - cache_entry["timestamp"] < self.max_age:
                    # Mettre à jour le cache en mémoire
                    self.memory_cache[key] = cache_entry
                    if self.logging: 
                        print(f"[CACHE-DISK] Hit pour {method}")
                    return cache_entry["data"]
            except (json.JSONDecodeError, KeyError):
                # En cas d'erreur, ignorer l'entrée du cache
                pass
        
        return None
    
    def set(self, method: str, data: Dict, **params) -> None:
        """
        Stocke un résultat dans le cache
        
        Args:
            method: Nom de la méthode d'API
            data: Résultat à mettre en cache
            params: Paramètres de la requête
        """
        key = self._get_cache_key(method, **params)
        cache_entry = {
            "timestamp": time.time(),
            "data": data
        }
        
        # Mettre à jour le cache en mémoire
        self.memory_cache[key] = cache_entry
        
        # Mettre à jour le cache sur disque
        file_path = self._get_cache_file_path(key)
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(cache_entry, f, ensure_ascii=False, indent=2)
            if self.logging:
                print(f"[CACHE] Sauvegarde pour {method}")
        except Exception as e:
            if self.logging:
                print(f"[CACHE] Erreur lors de la sauvegarde du cache: {e}")

class JDMClient:
    """Client pour l'API JDM"""
    
    def __init__(self, base_url: str = "https://jdm-api.demo.lirmm.fr", use_cache: bool = True, logging: bool = True):
        """
        Initialise le client JDM
        
        Args:
            base_url: URL de base de l'API JDM
            use_cache: Indique si le cache doit être utilisé
        """
        self.base_url = base_url
        self.use_cache = use_cache
        self.cache = JDMCache(logging=logging) # Ajouter un cache par défaut
        self.relation_type_ids = {}
        self.logging = logging
        self._initialize_relation_type_ids()
    
    def _initialize_relation_type_ids(self):
        """Initialise les IDs pour les types de relations 'r_agent' et 'r_isa'"""
        types = self.get_relation_types()
        for relation in types:
            name = relation.get("name")
            rel_id = relation.get("id")
            if name in ["r_agent", "r_agent-1", "r_isa", "r_hypo", "r_patient", "r_action_lieu", "r_time", "r_instr", "r_masc", "r_fem", "r_syn", "r_syn_strict"]:
                self.relation_type_ids[name] = rel_id
                logger.info(f"ID de la relation '${name}' : {rel_id}")

    def get_node_by_name(self, node_name: str) -> Dict[str, Any]:
        """
        Récupère un nœud par son nom
        
        Args:
            node_name: Nom du nœud
        
        Returns:
            Informations sur le nœud
        """
        # Vérifier d'abord le cache si activé
        if self.use_cache:
            cached_result = self.cache.get("get_node_by_name", node_name=node_name)
            if cached_result is not None:
                return cached_result
        
        url = f"{self.base_url}/v0/node_by_name/{node_name.lower()}"
        if self.logging:
            print(f"Requête GET: {url}")
        response = requests.get(url)
        if response.status_code != 200:
            print(f"Erreur {response.status_code}: {response.text}")
            return {"error": f"Erreur {response.status_code}", "node": None}
        result = response.json()
        
        # Mettre en cache le résultat si le cache est activé
        if self.use_cache:
            self.cache.set("get_node_by_name", result, node_name=node_name.lower())
            
        return result
    
    def get_relations_from(self, node_name: str, 
                          types_ids: Optional[List[int]] = None,
                          min_weight: Optional[int] = None,
                          max_weight: Optional[int] = None,
                          limit: int = None) -> Dict[str, Any]:
        """
        Récupère les relations sortantes d'un nœud
        
        Args:
            node_name: Nom du nœud source
            types_ids: IDs des types de relations à considérer
            min_weight: Poids minimum des relations
            limit: Nombre maximum de résultats
        
        Returns:
            Relations sortantes du nœud
        """
        # Vérifier d'abord le cache si activé
        if self.use_cache:
            cached_result = self.cache.get("get_relations_from", node_name=node_name.lower(), types_ids=types_ids, min_weight=min_weight, max_weight=max_weight, limit=limit)
            if cached_result is not None:
                return cached_result
        
        url = f"{self.base_url}/v0/relations/from/{node_name.lower()}"
        
        params = {}
        if types_ids:
            params["types_ids"] = types_ids
        if min_weight:
            params["min_weight"] = min_weight
        if max_weight:
            params["max_weight"] = max_weight
        if limit:
            params["limit"] = limit

        if self.logging:
            print(f"Requête GET: {url} avec params={params}")
        response = requests.get(url, params=params)
        if response.status_code != 200:
            print(f"Erreur {response.status_code}: {response.text}")
            return {"error": f"Erreur {response.status_code}", "nodes": [], "relations": []}
        result = response.json()
        
        # Mettre en cache le résultat si le cache est activé
        if self.use_cache:
            self.cache.set("get_relations_from", result, node_name=node_name.lower(), types_ids=types_ids, min_weight=min_weight, max_weight=max_weight, limit=limit)
            
        return result
    
    def get_relations_to(self, node_name: str, 
                        types_ids: Optional[List[int]] = None,
                        min_weight: Optional[int] = None,
                        max_weight: Optional[int] = None,
                        limit: int = None) -> Dict[str, Any]:
        """
        Récupère les relations entrantes vers un nœud
        
        Args:
            node_name: Nom du nœud cible
            types_ids: IDs des types de relations à considérer
            min_weight: Poids minimum des relations
            limit: Nombre maximum de résultats
        
        Returns:
            Relations entrantes vers le nœud
        """
        # Vérifier d'abord le cache si activé
        if self.use_cache:
            cached_result = self.cache.get("get_relations_to", node_name=node_name.lower(), types_ids=types_ids, min_weight=min_weight, max_weight=max_weight, limit=limit)
            if cached_result is not None:
                return cached_result
        
        url = f"{self.base_url}/v0/relations/to/{node_name.lower()}"
        
        params = {}
        if types_ids:
            params["types_ids"] = types_ids
        if min_weight:
            params["min_weight"] = min_weight
        if max_weight:
            params["max_weight"] = max_weight
        if limit:
            params["limit"] = limit
        
        if self.logging:
            print(f"Requête GET: {url} avec params={params}")
        response = requests.get(url, params=params)
        if response.status_code != 200:
            print(f"Erreur {response.status_code}: {response.text}")
            return {"error": f"Erreur {response.status_code}", "nodes": [], "relations": []}
        result = response.json()
        
        # Mettre en cache le résultat si le cache est activé
        if self.use_cache:
            self.cache.set("get_relations_to", result, node_name=node_name.lower(), types_ids=types_ids, min_weight=min_weight, max_weight=max_weight, limit=limit)
            
        return result
    
    def get_relations_from_to(self, node1_name: str, node2_name: str,
                             types_ids: Optional[List[int]] = None,
                             min_weight: Optional[int] = None,
                             max_weight: Optional[int] = None,
                             limit: int = None) -> Dict[str, Any]:
        """
        Récupère les relations entre deux nœuds
        
        Args:
            node1_name: Nom du nœud source
            node2_name: Nom du nœud cible
            types_ids: IDs des types de relations à considérer
            min_weight: Poids minimum des relations
            limit: Nombre maximum de résultats
        
        Returns:
            Relations entre les deux nœuds
        """

        # Vérifier d'abord le cache si activé
        if self.use_cache:
            cached_result = self.cache.get("get_relations_from_to", node1_name=node1_name.lower(), node2_name=node2_name.lower(), types_ids=types_ids, min_weight=min_weight, max_weight=max_weight, limit=limit)
            if cached_result is not None:
                return cached_result
        
        url = f"{self.base_url}/v0/relations/from/{node1_name.lower()}/to/{node2_name.lower()}"

        params = {}
        if types_ids:
            params["types_ids"] = types_ids
        if min_weight:
            params["min_weight"] = min_weight
        if max_weight:
            params["max_weight"] = max_weight
        if limit:
            params["limit"] = limit

        if self.logging:
            print(f"Requête GET: {url} avec params={params}")
        response = requests.get(url, params=params)
        if response.status_code != 200:
            print(f"Erreur {response.status_code}: {response.text}")
            #return {"nodes": [], "relations": []}
        
        result = response.json()

        # Mettre en cache le résultat si le cache est activé
        if self.use_cache:
            self.cache.set("get_relations_from_to", result, node1_name=node1_name.lower(), node2_name=node2_name.lower(), types_ids=types_ids, min_weight=min_weight, max_weight=max_weight, limit=limit)
            
        return result
    
    def get_relation_types(self) -> List[Dict[str, Any]]:
        """
        Récupère tous les types de relations
        
        Returns:
            Liste des types de relations
        """
        method = "get_relation_types"
        if self.use_cache:
            cached = self.cache.get(method)
            if cached:
                return cached

        url = f"{self.base_url}/v0/relations_types"
        print(f"Requête GET: {url}")
        
        # Ajouter un délai pour éviter de surcharger l'API
        time.sleep(0.5)
        
        response = requests.get(url)
        if response.status_code != 200:
            print(f"Erreur {response.status_code}: {response.text}")
            return []
        result = response.json();

        # Mettre en cache le résultat si le cache est activé
        if self.use_cache:
            self.cache.set("get_relation_types", result)
        
        return result

    def has_relation(self, source: str, target: str, relation_name: str) -> bool:
        """
        Vérifie si une relation de type `relation_name` existe entre `source` et `target`.
        La relation est directionnelle (source -> target).
        """
        source = source.lower()
        target = target.lower()

        relation_id = self.relation_type_ids.get(relation_name)
        if relation_id is None:
            logger.warning(f"Type de relation inconnu : {relation_name}")
            return False
        
        relations = self.get_relations_from_to(source, target, types_ids=[relation_id], min_weight=5, limit=50)

        return bool(relations and relations.get("relations"))

# Configuration du logger avec sortie dans un fichier
log_file_path = os.path.join("data", "jdm_client.log")
os.makedirs(os.path.dirname(log_file_path), exist_ok=True)
logger = logging.getLogger("JDMClient")
logger.setLevel(logging.INFO)
file_handler = logging.FileHandler(log_file_path, mode='w', encoding='utf-8')
file_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
logger.addHandler(file_handler)
logger.addHandler(logging.StreamHandler())

if __name__ == "__main__":
    # Exemple de test simple pour vérifier le fonctionnement du client
    client = JDMClient()
    mot = "chat"

    logger.info(f"--- Test: Récupération du noeud '{mot}' ---")
    noeud = client.get_node_by_name(mot)
    logger.info(json.dumps(noeud, indent=2, ensure_ascii=False))

    logger.info(f"--- Test: Relations sortantes de '{mot}' ---")
    relations_sortantes = client.get_relations_from(mot, limit=5)
    logger.info(json.dumps(relations_sortantes, indent=2, ensure_ascii=False))

    logger.info(f"--- Test: Relations entrantes vers '{mot}' ---")
    relations_entrantes = client.get_relations_to(mot, limit=5)
    logger.info(json.dumps(relations_entrantes, indent=2, ensure_ascii=False))

    logger.info(f"--- Test: Types de relations ---")
    types_relations = client.get_relation_types()
    logger.info(json.dumps(types_relations, indent=2, ensure_ascii=False))

    logger.info(f"--- Test: Existence d'une relation 'r_agent' entre 'chat' et 'manger' ---")
    exists = client.has_relation("manger", "chat", "r_agent")
    logger.info(f"Relation 'r_agent' entre 'chat' et 'manger' : {'OUI' if exists else 'NON'}")

    logger.info(f"--- Test: Existence d'une relation 'r_isa' entre 'chat' et 'animal' ---")
    exists = client.has_relation("animal", "chat", "r_isa")
    logger.info(f"Relation 'r_isa' entre 'animal' et 'chat' : {'OUI' if exists else 'NON'}")

    logger.info(f"--- Test: Existence d'une relation 'r_isa' entre 'chat' et 'animal' ---")
    exists = client.has_relation("chat", "animal", "r_isa")
    logger.info(f"Relation 'r_isa' entre 'chat' et 'animal' : {'OUI' if exists else 'NON'}")