import unittest
from datetime import datetime
from unittest.mock import patch
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from app.db.database import Base
from app.models.models import Category,Transaction,User
from app.services.feature3_insights_service import build_ai_insights_engine_response
from app.services.financial_context_service import build_financial_context
from app.services.prompt_builder_service import build_insights_prompt
from app.services.structured_insights_service import build_fallback_content,validate_llm_content

class Feature3Tests(unittest.TestCase):
    def setUp(self):
        engine=create_engine('sqlite://',connect_args={'check_same_thread':False},poolclass=StaticPool);Base.metadata.create_all(engine);self.db=sessionmaker(bind=engine)();self.user=User(name='Test',email='f3@test.com',password_hash='x');self.db.add(self.user);self.db.flush();food=Category(name='Food',color='#f00');self.db.add(food);self.db.flush()
        for desc,amount,kind,cat,balance,merchant,day in [('Salary',50000,'income',None,50000,'Employer',1),('Food',20000,'expense',food,30000,'Delivery App',5)]:self.db.add(Transaction(user_id=self.user.id,amount=amount,category_id=cat.id if cat else None,description=desc,merchant=merchant,extracted_merchant=merchant,transaction_type=kind,date=datetime(2026,5,day),balance=balance))
        self.db.commit()
    def tearDown(self):self.db.close()
    def test_context_and_prompt(self):
        c=build_financial_context(self.db,self.user.id,5,2026);self.assertEqual(c.core_metrics.total_income,50000);self.assertIn('Do not invent or recalculate',build_insights_prompt(c))
    def test_fallback_groups(self):
        x=build_fallback_content(build_financial_context(self.db,self.user.id,5,2026));self.assertTrue(x.spending_insights and x.savings_insights and x.health_insights and x.recommendations)
    def test_bad_json(self):self.assertIsNone(validate_llm_content('bad'))
    @patch('app.services.feature3_insights_service.InsightsLLMService.generate',return_value=(None,'deterministic'))
    def test_response(self,_):
        x=build_ai_insights_engine_response(self.db,self.user.id,5,2026);self.assertEqual(x.provider,'deterministic');self.assertEqual(x.health_score,x.context.health_score.overall_score);self.assertTrue(x.top_priority)

if __name__=='__main__':unittest.main()
