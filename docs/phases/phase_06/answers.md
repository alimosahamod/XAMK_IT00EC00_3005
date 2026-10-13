# Phase 6 — Answers

## A. Pattern

### 1. Intent of Strategy

Strategy puts each algorithm in his own class behind one interface, so the algorithms can be switched. The context holds a strategy object and only calls his method, here decide(context). It doesnt know the formula inside. For choosing the algorithm and running it, it must stay separate. Otherwise the context needs an if-branch for every algorithm, and every new algorithm means changing the context.

### 2. Participants

The strategy is the interface, here AutomationStrategy. 
The concrete strategies are the real algorithms, here ConservativeMoistureStrategy and AggressiveMoistureStrategy. 
The context uses a strategy, here AutomationService. 
The client chooses the strategy, here the PUT endpoint and the StrategyPanel that save the key.

 If all rules are if/elif inside the router, this one method grows with every rule. Rules cant be tested alone, two developers change the same code, and a mistake in one rule can break the others.

### 3. When to use it

Use Strategy when there are different ways to do the same task and you want to choose /change them without editing the context. Skip it when there is only one algorithm, because the additional classes only add code. Also it can be skipped when the behavior changes because the object moves through a lifecycle, like open and closed, then State fits better.

## B. This phase of the application

### 4. What decide returns

decide(context) returns a Recommendation with an action (irrigate or wait), a reason and an optional score. Conservative waters only below the low threshold. Aggressive already waters below the middle of the band. With the band 0.25–0.45 and moisture 0.30, conservative says wait and aggressive says irrigate.

### 5. Where the numbers come from

The moisture is the newest value in sensor_readings from a moisture sensor linked to this location. Low and high come from the zones of the location. The service builds the context from these numbers. Strategies get a plain object, so they do not depend on the database or the framework, and they are easy to test with a fake context. Thresholds come from zones because every zone could need different values and the operator can change them without changing code.

### 6. Why evaluate uses the saved key

The saved key is the real setting of the location. Every client and later the automation itself, gets the same result. A key in the request could differ from what is saved, so the UI would show something that is not really active. If the operator changes the strategy and moisture stays the same, the next evaluate uses the new key and can give a different answer, for example wait before and irrigate after.

### 7. Decide vs execute

Deciding and acting are different from each other. If decide() started the pump, every evaluate or test would water the plants. We also could not log, undo, confirm or check the action before it runs. The strategy only recommends. The Command pattern in a later phase will carry out the action.

## C. Compare, contrast, and scenarios

### 8. Strategy vs State

Both delegate to an object with the same interface. In Strategy the client chooses the object, e.g. the operator picks conservative, it's a policy. In State the object changes itself when his internal state changes, for example from open to closed, then it's is a lifecycle.

### 9. Strategy vs Adapter vs Builder

- Adapter translates a foreign API into our interface, like the vendor sensor data into a Reading. 
- Builder assembles a valid object step by step, like a location with its zones. 
- Strategy switch an algorithm, like conservative or aggressive watering.

### 10. Two traps

A mega strategy with if conservative /if aggressive inside is just the old if/elif in a new place. A new rule still means editing this class, and the rules arent separate. A strategy that calls the actuator adapter mixes decision-making with execution. As a result, every code review waters the plants, and tests require hardware or mocks. Furthermore, commands cannot control, log, or undo the action.

Claude Code and Google Gemini was used to translate the answers and help me writing the code + to formulate complete sentences