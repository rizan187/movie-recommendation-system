from Main import app, db  
import Main.models        

with app.app_context():
    db.create_all()
    print("All tables created!")
