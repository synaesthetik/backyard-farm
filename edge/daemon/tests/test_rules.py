from rules import LocalRuleEngine, RuleAction


def test_emergency_shutoff_above_threshold():
    engine = LocalRuleEngine(node_type="zone")
    results = engine.evaluate({"moisture": 96.0})
    assert len(results) == 1
    assert results[0].action == RuleAction.IRRIGATION_SHUTOFF


def test_no_shutoff_below_threshold():
    engine = LocalRuleEngine(node_type="zone")
    results = engine.evaluate({"moisture": 94.0})
    assert len(results) == 0


def test_shutoff_at_exact_threshold():
    engine = LocalRuleEngine(node_type="zone")
    results = engine.evaluate({"moisture": 95.0})
    assert len(results) == 1
    assert results[0].action == RuleAction.IRRIGATION_SHUTOFF


def test_coop_hard_close_at_hour():
    engine = LocalRuleEngine(node_type="coop")
    results = engine.evaluate({}, current_hour=21)
    assert len(results) == 1
    assert results[0].action == RuleAction.COOP_HARD_CLOSE


def test_coop_no_close_before_hour():
    engine = LocalRuleEngine(node_type="coop")
    results = engine.evaluate({}, current_hour=20)
    assert len(results) == 0


def test_coop_close_past_hour():
    engine = LocalRuleEngine(node_type="coop")
    results = engine.evaluate({}, current_hour=22)
    assert len(results) == 1
    assert results[0].action == RuleAction.COOP_HARD_CLOSE


def test_zone_ignores_coop_rules():
    engine = LocalRuleEngine(node_type="zone")
    results = engine.evaluate({"moisture": 50.0}, current_hour=23)
    assert len(results) == 0


def test_coop_ignores_zone_rules():
    engine = LocalRuleEngine(node_type="coop")
    results = engine.evaluate({"moisture": 99.0}, current_hour=10)
    assert len(results) == 0


def test_custom_threshold():
    engine = LocalRuleEngine(node_type="zone", moisture_shutoff_vwc=90.0)
    results = engine.evaluate({"moisture": 91.0})
    assert len(results) == 1
    assert results[0].action == RuleAction.IRRIGATION_SHUTOFF
