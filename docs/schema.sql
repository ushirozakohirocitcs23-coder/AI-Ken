-- AI-KEN database schema (PostgreSQL). Generated from app/models.py.

CREATE TABLE dictionary_entries (
	id SERIAL NOT NULL, 
	word VARCHAR(80) NOT NULL, 
	language VARCHAR(20) NOT NULL, 
	part_of_speech VARCHAR(40), 
	definition TEXT NOT NULL, 
	synonyms JSON, 
	antonyms JSON, 
	example TEXT, 
	emotion_category VARCHAR(40), 
	literary_usage TEXT, 
	level VARCHAR(20) NOT NULL, 
	source VARCHAR(300) NOT NULL, 
	source_url VARCHAR(500), 
	verified BOOLEAN NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	updated_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	PRIMARY KEY (id), 
	CONSTRAINT uq_dict_word_lang UNIQUE (word, language)
);

CREATE INDEX ix_dictionary_entries_language ON dictionary_entries (language);
CREATE INDEX ix_dictionary_entries_emotion_category ON dictionary_entries (emotion_category);
CREATE INDEX ix_dictionary_entries_word ON dictionary_entries (word);

CREATE TABLE kb_chunks (
	id SERIAL NOT NULL, 
	source_type VARCHAR(20) NOT NULL, 
	source_id INTEGER NOT NULL, 
	language VARCHAR(20) NOT NULL, 
	category VARCHAR(40), 
	text TEXT NOT NULL, 
	embedding BYTEA NOT NULL, 
	embedding_model VARCHAR(120) NOT NULL, 
	dim INTEGER NOT NULL, 
	PRIMARY KEY (id)
);

CREATE INDEX ix_kb_chunks_category ON kb_chunks (category);
CREATE INDEX ix_chunk_source ON kb_chunks (source_type, source_id);
CREATE INDEX ix_kb_chunks_embedding_model ON kb_chunks (embedding_model);

CREATE TABLE poetry_forms (
	id SERIAL NOT NULL, 
	key VARCHAR(40) NOT NULL, 
	name VARCHAR(80) NOT NULL, 
	language VARCHAR(20) NOT NULL, 
	tradition VARCHAR(40) NOT NULL, 
	description TEXT NOT NULL, 
	rules JSON NOT NULL, 
	guidance TEXT NOT NULL, 
	source_references TEXT, 
	enabled BOOLEAN NOT NULL, 
	updated_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	PRIMARY KEY (id)
);

CREATE UNIQUE INDEX ix_poetry_forms_key ON poetry_forms (key);

CREATE TABLE rag_logs (
	id SERIAL NOT NULL, 
	stage VARCHAR(30) NOT NULL, 
	ok BOOLEAN NOT NULL, 
	latency_ms INTEGER NOT NULL, 
	result_count INTEGER, 
	top_score FLOAT, 
	detail VARCHAR(500), 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	PRIMARY KEY (id)
);

CREATE INDEX ix_rag_logs_stage ON rag_logs (stage);
CREATE INDEX ix_rag_logs_created_at ON rag_logs (created_at);

CREATE TABLE system_settings (
	key VARCHAR(80) NOT NULL, 
	value JSON, 
	updated_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	PRIMARY KEY (key)
);


CREATE TABLE users (
	id SERIAL NOT NULL, 
	full_name VARCHAR(120) NOT NULL, 
	email VARCHAR(255) NOT NULL, 
	password_hash VARCHAR(255) NOT NULL, 
	role VARCHAR(20) NOT NULL, 
	status VARCHAR(20) NOT NULL, 
	last_login_at TIMESTAMP WITH TIME ZONE, 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	updated_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	PRIMARY KEY (id)
);

CREATE UNIQUE INDEX ix_users_email ON users (email);
CREATE INDEX ix_users_status ON users (status);
CREATE INDEX ix_users_role ON users (role);
CREATE INDEX ix_users_created_at ON users (created_at);

CREATE TABLE audit_logs (
	id SERIAL NOT NULL, 
	actor_id INTEGER, 
	action VARCHAR(80) NOT NULL, 
	target VARCHAR(120), 
	meta JSON, 
	ip VARCHAR(64), 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(actor_id) REFERENCES users (id) ON DELETE SET NULL
);

CREATE INDEX ix_audit_logs_created_at ON audit_logs (created_at);
CREATE INDEX ix_audit_logs_action ON audit_logs (action);
CREATE INDEX ix_audit_logs_actor_id ON audit_logs (actor_id);

CREATE TABLE conversations (
	id SERIAL NOT NULL, 
	user_id INTEGER NOT NULL, 
	title VARCHAR(200) NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	updated_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE CASCADE
);

CREATE INDEX ix_conversations_updated_at ON conversations (updated_at);
CREATE INDEX ix_conversations_user_id ON conversations (user_id);

CREATE TABLE knowledge_documents (
	id SERIAL NOT NULL, 
	title VARCHAR(200) NOT NULL, 
	source VARCHAR(500), 
	language VARCHAR(20) NOT NULL, 
	doc_type VARCHAR(40) NOT NULL, 
	content TEXT NOT NULL, 
	content_meta JSON, 
	status VARCHAR(20) NOT NULL, 
	error TEXT, 
	chunk_count INTEGER NOT NULL, 
	is_system BOOLEAN NOT NULL, 
	uploaded_by INTEGER, 
	uploaded_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	processed_at TIMESTAMP WITH TIME ZONE, 
	PRIMARY KEY (id), 
	FOREIGN KEY(uploaded_by) REFERENCES users (id) ON DELETE SET NULL
);


CREATE TABLE password_resets (
	id SERIAL NOT NULL, 
	user_id INTEGER NOT NULL, 
	token_hash VARCHAR(64) NOT NULL, 
	expires_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	used BOOLEAN NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE CASCADE
);

CREATE UNIQUE INDEX ix_password_resets_token_hash ON password_resets (token_hash);
CREATE INDEX ix_password_resets_user_id ON password_resets (user_id);

CREATE TABLE sessions (
	id SERIAL NOT NULL, 
	user_id INTEGER NOT NULL, 
	token_hash VARCHAR(64) NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	expires_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	user_agent VARCHAR(255), 
	PRIMARY KEY (id), 
	FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE CASCADE
);

CREATE UNIQUE INDEX ix_sessions_token_hash ON sessions (token_hash);
CREATE INDEX ix_sessions_user_id ON sessions (user_id);

CREATE TABLE poems (
	id SERIAL NOT NULL, 
	user_id INTEGER NOT NULL, 
	conversation_id INTEGER, 
	story_message_id INTEGER, 
	parent_poem_id INTEGER, 
	title VARCHAR(200) NOT NULL, 
	content TEXT NOT NULL, 
	detected_emotions JSON, 
	analysis JSON, 
	language VARCHAR(20) NOT NULL, 
	poem_type VARCHAR(40) NOT NULL, 
	rhyme_scheme VARCHAR(40), 
	settings JSON, 
	validation JSON, 
	vocabulary JSON, 
	retrieval JSON, 
	kind VARCHAR(20) NOT NULL, 
	is_saved BOOLEAN NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE CASCADE, 
	FOREIGN KEY(conversation_id) REFERENCES conversations (id) ON DELETE CASCADE
);

CREATE INDEX ix_poems_is_saved ON poems (is_saved);
CREATE INDEX ix_poems_conversation_id ON poems (conversation_id);
CREATE INDEX ix_poems_user_id ON poems (user_id);
CREATE INDEX ix_poems_created_at ON poems (created_at);
CREATE INDEX ix_poems_language ON poems (language);
CREATE INDEX ix_poems_poem_type ON poems (poem_type);

CREATE TABLE feedback (
	id SERIAL NOT NULL, 
	user_id INTEGER NOT NULL, 
	poem_id INTEGER NOT NULL, 
	rating INTEGER NOT NULL, 
	comments TEXT, 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	PRIMARY KEY (id), 
	CONSTRAINT uq_feedback_user_poem UNIQUE (user_id, poem_id), 
	FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE CASCADE, 
	FOREIGN KEY(poem_id) REFERENCES poems (id) ON DELETE CASCADE
);

CREATE INDEX ix_feedback_user_id ON feedback (user_id);
CREATE INDEX ix_feedback_poem_id ON feedback (poem_id);

CREATE TABLE messages (
	id SERIAL NOT NULL, 
	conversation_id INTEGER NOT NULL, 
	sender VARCHAR(20) NOT NULL, 
	content TEXT NOT NULL, 
	poem_id INTEGER, 
	meta JSON, 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(conversation_id) REFERENCES conversations (id) ON DELETE CASCADE, 
	FOREIGN KEY(poem_id) REFERENCES poems (id) ON DELETE SET NULL
);

CREATE INDEX ix_messages_conversation_id ON messages (conversation_id);
