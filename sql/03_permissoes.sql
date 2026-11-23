-- No master, crie um login SQL dedicado conforme seu ambiente.
-- Na base PIMVI, substitua o identificador pimvi_app se necessário.
CREATE USER pimvi_app FOR LOGIN pimvi_app;
GRANT SELECT, INSERT, UPDATE ON SCHEMA::clin TO pimvi_app;
