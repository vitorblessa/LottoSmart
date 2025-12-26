import requests
import sys
import json
from datetime import datetime

class LotteryAPITester:
    def __init__(self, base_url="https://lucky-numbers-211.preview.emergentagent.com/api"):
        self.base_url = base_url
        self.tests_run = 0
        self.tests_passed = 0
        self.test_results = []

    def run_test(self, name, method, endpoint, expected_status, data=None, params=None):
        """Run a single API test"""
        url = f"{self.base_url}/{endpoint}"
        headers = {'Content-Type': 'application/json'}

        self.tests_run += 1
        print(f"\n🔍 Testing {name}...")
        print(f"   URL: {url}")
        
        try:
            if method == 'GET':
                response = requests.get(url, headers=headers, params=params, timeout=30)
            elif method == 'POST':
                response = requests.post(url, json=data, headers=headers, params=params, timeout=30)
            elif method == 'DELETE':
                response = requests.delete(url, headers=headers, timeout=30)

            success = response.status_code == expected_status
            
            if success:
                self.tests_passed += 1
                print(f"✅ Passed - Status: {response.status_code}")
                try:
                    response_data = response.json()
                    if 'success' in response_data:
                        print(f"   Success: {response_data['success']}")
                    if 'data' in response_data and isinstance(response_data['data'], dict):
                        # Show some key info without overwhelming output
                        if 'concurso' in response_data['data']:
                            print(f"   Concurso: {response_data['data']['concurso']}")
                        if 'dezenas' in response_data['data']:
                            print(f"   Numbers: {response_data['data']['dezenas']}")
                        if 'total_draws_analyzed' in response_data['data']:
                            print(f"   Draws analyzed: {response_data['data']['total_draws_analyzed']}")
                except:
                    pass
            else:
                print(f"❌ Failed - Expected {expected_status}, got {response.status_code}")
                try:
                    error_data = response.json()
                    print(f"   Error: {error_data}")
                except:
                    print(f"   Response: {response.text[:200]}")

            self.test_results.append({
                "name": name,
                "method": method,
                "endpoint": endpoint,
                "expected_status": expected_status,
                "actual_status": response.status_code,
                "success": success,
                "response_size": len(response.text) if response.text else 0
            })

            return success, response.json() if success and response.text else {}

        except Exception as e:
            print(f"❌ Failed - Error: {str(e)}")
            self.test_results.append({
                "name": name,
                "method": method,
                "endpoint": endpoint,
                "expected_status": expected_status,
                "actual_status": "ERROR",
                "success": False,
                "error": str(e)
            })
            return False, {}

    def test_root_endpoint(self):
        """Test root API endpoint"""
        return self.run_test("Root API", "GET", "", 200)

    def test_quina_latest(self):
        """Test Quina latest result"""
        return self.run_test("Quina Latest Result", "GET", "lottery/quina/latest", 200)

    def test_dupla_sena_latest(self):
        """Test Dupla Sena latest result"""
        return self.run_test("Dupla Sena Latest Result", "GET", "lottery/dupla_sena/latest", 200)

    def test_quina_statistics(self):
        """Test Quina statistics"""
        return self.run_test("Quina Statistics", "GET", "lottery/quina/statistics", 200)

    def test_dupla_sena_statistics(self):
        """Test Dupla Sena statistics"""
        return self.run_test("Dupla Sena Statistics", "GET", "lottery/dupla_sena/statistics", 200)

    def test_quina_next_draw(self):
        """Test Quina next draw info"""
        return self.run_test("Quina Next Draw", "GET", "lottery/quina/next-draw", 200)

    def test_dupla_sena_next_draw(self):
        """Test Dupla Sena next draw info"""
        return self.run_test("Dupla Sena Next Draw", "GET", "lottery/dupla_sena/next-draw", 200)

    def test_quina_history(self):
        """Test Quina history"""
        return self.run_test("Quina History", "GET", "lottery/quina/history", 200, params={"limit": 5})

    def test_dupla_sena_history(self):
        """Test Dupla Sena history"""
        return self.run_test("Dupla Sena History", "GET", "lottery/dupla_sena/history", 200, params={"limit": 5})

    def test_generate_quina_bets(self):
        """Test generating Quina bets"""
        return self.run_test(
            "Generate Quina Bets", 
            "POST", 
            "bets/generate", 
            200,
            params={"lottery_type": "quina", "strategy": "balanced", "count": 2}
        )

    def test_generate_dupla_sena_bets(self):
        """Test generating Dupla Sena bets"""
        return self.run_test(
            "Generate Dupla Sena Bets", 
            "POST", 
            "bets/generate", 
            200,
            params={"lottery_type": "dupla_sena", "strategy": "hot", "count": 1}
        )

    def test_save_bet(self):
        """Test saving a bet"""
        bet_data = {
            "lottery_type": "quina",
            "numbers": [5, 15, 25, 35, 45],
            "strategy": "manual",
            "explanation": "Test bet for API testing"
        }
        return self.run_test("Save Bet", "POST", "bets", 200, data=bet_data)

    def test_save_duplicate_bet(self):
        """Test saving duplicate bet (should return 409)"""
        bet_data = {
            "lottery_type": "quina",
            "numbers": [5, 15, 25, 35, 45],
            "strategy": "manual",
            "explanation": "Duplicate test bet"
        }
        return self.run_test("Save Duplicate Bet", "POST", "bets", 409, data=bet_data)

    def test_get_bets(self):
        """Test getting saved bets"""
        return self.run_test("Get All Bets", "GET", "bets", 200, params={"limit": 10})

    def test_get_quina_bets(self):
        """Test getting Quina bets only"""
        return self.run_test("Get Quina Bets", "GET", "bets", 200, params={"lottery_type": "quina", "limit": 5})

    def test_check_bet(self, bet_id):
        """Test checking a bet against latest result"""
        return self.run_test(f"Check Bet {bet_id}", "POST", f"bets/check/{bet_id}", 200)

    def test_check_all_bets(self):
        """Test checking all unchecked bets"""
        return self.run_test("Check All Bets", "POST", "bets/check-all", 200)

    def test_delete_bet(self, bet_id):
        """Test deleting a bet"""
        return self.run_test(f"Delete Bet {bet_id}", "DELETE", f"bets/{bet_id}", 200)

    def test_invalid_lottery_type(self):
        """Test invalid lottery type"""
        return self.run_test("Invalid Lottery Type", "GET", "lottery/invalid/latest", 400)

    def test_invalid_strategy(self):
        """Test invalid strategy"""
        return self.run_test(
            "Invalid Strategy", 
            "POST", 
            "bets/generate", 
            400,
            params={"lottery_type": "quina", "strategy": "invalid", "count": 1}
        )

def main():
    print("🎲 Starting Lottery API Tests...")
    print("=" * 60)
    
    tester = LotteryAPITester()
    
    # Test basic endpoints
    print("\n📡 Testing Basic API Endpoints...")
    tester.test_root_endpoint()
    
    # Test lottery data endpoints
    print("\n🎯 Testing Lottery Data Endpoints...")
    tester.test_quina_latest()
    tester.test_dupla_sena_latest()
    tester.test_quina_next_draw()
    tester.test_dupla_sena_next_draw()
    tester.test_quina_history()
    tester.test_dupla_sena_history()
    
    # Test statistics endpoints
    print("\n📊 Testing Statistics Endpoints...")
    tester.test_quina_statistics()
    tester.test_dupla_sena_statistics()
    
    # Test bet generation
    print("\n🎰 Testing Bet Generation...")
    tester.test_generate_quina_bets()
    tester.test_generate_dupla_sena_bets()
    
    # Test bet management
    print("\n💾 Testing Bet Management...")
    success, bet_response = tester.test_save_bet()
    bet_id = None
    if success and 'data' in bet_response and 'id' in bet_response['data']:
        bet_id = bet_response['data']['id']
        print(f"   Created bet with ID: {bet_id}")
    
    tester.test_save_duplicate_bet()
    tester.test_get_bets()
    tester.test_get_quina_bets()
    
    # Test bet checking and deletion if we have a bet ID
    if bet_id:
        print("\n🔍 Testing Bet Operations...")
        tester.test_check_bet(bet_id)
        tester.test_check_all_bets()
        tester.test_delete_bet(bet_id)
    
    # Test error cases
    print("\n❌ Testing Error Cases...")
    tester.test_invalid_lottery_type()
    tester.test_invalid_strategy()
    
    # Print final results
    print("\n" + "=" * 60)
    print(f"📊 Test Results: {tester.tests_passed}/{tester.tests_run} passed")
    
    if tester.tests_passed == tester.tests_run:
        print("🎉 All tests passed!")
        return 0
    else:
        failed_tests = [t for t in tester.test_results if not t['success']]
        print(f"❌ {len(failed_tests)} tests failed:")
        for test in failed_tests:
            error_msg = test.get('error', f"Status {test['actual_status']}")
            print(f"   - {test['name']}: {error_msg}")
        return 1

if __name__ == "__main__":
    sys.exit(main())