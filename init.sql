
-- =====================================================
-- DEMO TEXT-TO-SQL : base de données entreprise
-- Toutes les tables sont isolées dans le schema text2sql_demo
-- =====================================================

CREATE SCHEMA IF NOT EXISTS text2sql_demo;

DROP TABLE IF EXISTS text2sql_demo.lignes_commandes CASCADE;
DROP TABLE IF EXISTS text2sql_demo.commandes CASCADE;
DROP TABLE IF EXISTS text2sql_demo.produits CASCADE;
DROP TABLE IF EXISTS text2sql_demo.clients CASCADE;
DROP TABLE IF EXISTS text2sql_demo.employes CASCADE;
DROP TABLE IF EXISTS text2sql_demo.departements CASCADE;

-- =====================================================
-- 1. DEPARTEMENTS
-- =====================================================

CREATE TABLE text2sql_demo.departements (
    id SERIAL PRIMARY KEY,
    nom VARCHAR(100) NOT NULL,
    ville VARCHAR(100) NOT NULL
);

INSERT INTO text2sql_demo.departements (nom, ville) VALUES
('Informatique', 'Lyon'),
('Commercial', 'Paris'),
('Finance', 'Lyon'),
('Ressources Humaines', 'Marseille'),
('Marketing', 'Paris');

-- =====================================================
-- 2. EMPLOYES
-- =====================================================

CREATE TABLE text2sql_demo.employes (
    id SERIAL PRIMARY KEY,
    nom VARCHAR(100) NOT NULL,
    prenom VARCHAR(100) NOT NULL,
    email VARCHAR(150) UNIQUE,
    salaire NUMERIC(10,2),
    date_embauche DATE,
    departement_id INTEGER REFERENCES text2sql_demo.departements(id)
);

INSERT INTO text2sql_demo.employes
(nom, prenom, email, salaire, date_embauche, departement_id)
VALUES
('Martin', 'Paul', 'paul.martin@entreprise.fr', 4200, '2020-03-15', 1),
('Durand', 'Sophie', 'sophie.durand@entreprise.fr', 3800, '2021-06-01', 1),
('Bernard', 'Thomas', 'thomas.bernard@entreprise.fr', 5100, '2018-09-10', 2),
('Petit', 'Julie', 'julie.petit@entreprise.fr', 3500, '2022-01-20', 3),
('Robert', 'Lucas', 'lucas.robert@entreprise.fr', 4000, '2019-11-05', 4),
('Richard', 'Emma', 'emma.richard@entreprise.fr', 3900, '2023-04-12', 5),
('Moreau', 'Antoine', 'antoine.moreau@entreprise.fr', 4600, '2017-07-01', 1);

-- =====================================================
-- 3. CLIENTS
-- =====================================================

CREATE TABLE text2sql_demo.clients (
    id SERIAL PRIMARY KEY,
    nom VARCHAR(150) NOT NULL,
    email VARCHAR(150) UNIQUE,
    ville VARCHAR(100),
    pays VARCHAR(100),
    date_creation DATE NOT NULL
);

INSERT INTO text2sql_demo.clients
(nom, email, ville, pays, date_creation)
SELECT
    'Client ' || n,
    'client' || n || '@example.fr',
    (ARRAY['Lyon', 'Paris', 'Marseille', 'Bordeaux', 'Lille'])[1 + (n % 5)],
    'France',
    DATE '2023-01-01' + (n * 7)
FROM generate_series(1, 50) AS n;

-- =====================================================
-- 4. PRODUITS
-- =====================================================

CREATE TABLE text2sql_demo.produits (
    id SERIAL PRIMARY KEY,
    nom VARCHAR(150) NOT NULL,
    categorie VARCHAR(100),
    prix NUMERIC(10,2) NOT NULL,
    stock INTEGER NOT NULL DEFAULT 0
);

INSERT INTO text2sql_demo.produits (nom, categorie, prix, stock) VALUES
('Ordinateur portable', 'Informatique', 1200, 15),
('Ecran 27 pouces', 'Informatique', 320, 30),
('Clavier mécanique', 'Informatique', 95, 50),
('Souris sans fil', 'Informatique', 45, 80),
('Station d accueil', 'Informatique', 180, 20),
('Bureau ergonomique', 'Mobilier', 450, 12),
('Chaise de bureau', 'Mobilier', 290, 18),
('Lampe de bureau', 'Mobilier', 65, 40),
('Casque audio', 'Accessoires', 130, 35),
('Webcam HD', 'Accessoires', 85, 25),
('Disque SSD 1 To', 'Informatique', 110, 45),
('Sacoche ordinateur', 'Accessoires', 55, 60);

-- =====================================================
-- 5. COMMANDES
-- =====================================================

CREATE TABLE text2sql_demo.commandes (
    id SERIAL PRIMARY KEY,
    client_id INTEGER NOT NULL REFERENCES text2sql_demo.clients(id),
    employe_id INTEGER REFERENCES text2sql_demo.employes(id),
    date_commande DATE NOT NULL,
    statut VARCHAR(30) NOT NULL
        CHECK (statut IN ('en_attente', 'payee', 'expediee', 'livree', 'annulee'))
);

INSERT INTO text2sql_demo.commandes
(client_id, employe_id, date_commande, statut)
SELECT
    1 + (n % 50),
    1 + (n % 7),
    DATE '2025-01-01' + (n * 3),
    (ARRAY['en_attente', 'payee', 'expediee', 'livree', 'annulee'])[1 + (n % 5)]
FROM generate_series(1, 100) AS n;

-- =====================================================
-- 6. LIGNES DE COMMANDES
-- =====================================================

CREATE TABLE text2sql_demo.lignes_commandes (
    id SERIAL PRIMARY KEY,
    commande_id INTEGER NOT NULL REFERENCES text2sql_demo.commandes(id),
    produit_id INTEGER NOT NULL REFERENCES text2sql_demo.produits(id),
    quantite INTEGER NOT NULL CHECK (quantite > 0),
    prix_unitaire NUMERIC(10,2) NOT NULL
);

INSERT INTO text2sql_demo.lignes_commandes
(commande_id, produit_id, quantite, prix_unitaire)
SELECT
    c.id,
    1 + ((c.id + g.n) % 12),
    1 + (c.id % 4),
    p.prix
FROM text2sql_demo.commandes c
CROSS JOIN generate_series(1, 2) AS g(n)
JOIN text2sql_demo.produits p
    ON p.id = 1 + ((c.id + g.n) % 12);

-- =====================================================
-- FIN : quelques statistiques
-- =====================================================

SELECT 'departements' AS table_name, COUNT(*) AS total
FROM text2sql_demo.departements
UNION ALL
SELECT 'employes', COUNT(*) FROM text2sql_demo.employes
UNION ALL
SELECT 'clients', COUNT(*) FROM text2sql_demo.clients
UNION ALL
SELECT 'produits', COUNT(*) FROM text2sql_demo.produits
UNION ALL
SELECT 'commandes', COUNT(*) FROM text2sql_demo.commandes
UNION ALL
SELECT 'lignes_commandes', COUNT(*) FROM text2sql_demo.lignes_commandes;

-- =====================================================
-- 7. UTILISATEUR EN LECTURE SEULE POUR L'AGENT IA
-- =====================================================

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT FROM pg_roles WHERE rolname = 'ai_reader'
    ) THEN
        CREATE ROLE ai_reader LOGIN PASSWORD 'ai_reader_demo';
    END IF;
END
$$;

-- Accès au schéma
GRANT USAGE ON SCHEMA text2sql_demo TO ai_reader;

-- Lecture seule sur les tables existantes
GRANT SELECT ON ALL TABLES IN SCHEMA text2sql_demo TO ai_reader;

-- Lecture seule automatique sur les futures tables
ALTER DEFAULT PRIVILEGES IN SCHEMA text2sql_demo
GRANT SELECT ON TABLES TO ai_reader;
