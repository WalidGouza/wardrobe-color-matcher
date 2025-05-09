CREATE TABLE Wardrobe (
	id int PRIMARY KEY
);

CREATE TABLE Clothing_items (
	wardrobe_id int NOT NULL,
	type varchar(20) NOT NULL,
	r int,
	g int,
	b int,
	CONSTRAINT wardrobe FOREIGN KEY (wardrobe_id) REFERENCES Wardrobe(id)
);

-- INSERT INTO Wardrobe VALUES (1);

-- ALTER TABLE clothing_items
-- ADD COLUMN id SERIAL PRIMARY KEY;
