# City Cog Development Plan

## Current Modules

### 1. Crime Module
#### Jail System Refactoring Plan
1. **Create Dedicated Jail Module** (`city/crime/jail.py`) ✅
   - Core JailManager class ✅
   - Centralized state management ✅
   - Standardized error handling ✅
   - Event dispatching system ✅

2. **JailManager Class Structure**
   ```python
   class JailManager:
       # Core Jail Functions ✅
       - get_jail_time_remaining(member)
       - send_to_jail(member, time, channel)
       - release_from_jail(member)
       - is_in_jail(member)
       
       # Bail System ✅
       - calculate_bail_cost(remaining_time)
       - process_bail_payment(member, amount)
       - can_pay_bail(member)
       - format_bail_embed(member)
       
       # Jailbreak System
       - get_jailbreak_scenario()
       - process_jailbreak_attempt(member)
       - apply_jailbreak_event(member, event)
       
       # Perk Management ✅
       - apply_sentence_reduction(time)
       - has_jail_reducer(member)
       
       # Notification System ✅
       - schedule_release_notification(member)
       - cancel_notification(member)
       - send_notification(member, channel)
       
       # State Management ✅
       - get_jail_state(member)
       - update_jail_state(member, state)
       - clear_jail_state(member)
   ```

3. **Implementation Phases**

   a) Core Infrastructure ✅
      - [x] Create JailManager class
      - [x] Implement state management
      - [x] Set up error handling system
      - [x] Add logging and debugging

   b) Feature Migration
      - [x] Move jail time calculations
      - [x] Migrate bail system
      - [x] Transfer jailbreak mechanics
      - [x] Port notification system

   c) Integration Updates
      - [ ] Update command handlers
      - [ ] Modify view classes
      - [ ] Adjust crime scenarios
      - [ ] Update black market integration

4. **Data Structure Updates** ✅
   ```python
   JailState = {
       "jail_until": int,
       "attempted_jailbreak": bool,
       "jail_channel": Optional[int],
       "notify_on_release": bool,
       "reduced_sentence": bool,
       "original_sentence": int
   }
   ```

5. **Error Handling** ✅
   - Custom exception classes
   - Standardized error messages
   - Proper error propagation
   - Recovery mechanisms

6. **Migration Strategy**

   a) Phase 1: Parallel Implementation
      - [x] Implement new system alongside existing
      - [ ] Validate all functionality

   b) Phase 2: Cleanup
      - [ ] Remove old implementation
      - [ ] Clean up imports
      - [ ] Update documentation

7. **Validation Checklist**
   - [ ] All existing features work
   - [ ] UI remains unchanged
   - [ ] Perks function correctly
   - [ ] Notifications work reliably
   - [ ] No performance regression
   - [ ] State consistency maintained
   - [ ] Error handling improved

#### Next Steps (Priority Order)
- [ ] Implement jailbreak refactor
- [ ] Update command handlers and views
- [ ] New Features
  - [ ] "The Purge" blackmarket item implementation
  - [ ] Additional balancing and tweaks
  - [ ] More custom scenarios

### 2. Business Module (In Development)
#### Core Features
- [ ] Business creation and management
- [ ] Multiple industry types
  - [ ] Trading
  - [ ] Manufacturing
  - [ ] Retail
- [ ] Vault system
- [ ] Passive income generation
- [ ] Business robbery mechanics
- [ ] Security systems

#### Business UI
- [ ] Business management interface
- [ ] Shop interface
- [ ] Status displays
- [ ] Transaction history

#### Business Progression
- [ ] Level system
- [ ] Upgrades shop
- [ ] Industry-specific perks
- [ ] Achievement system

## Planned Modules

### TBA

## Technical Improvements

### Performance
- [ ] Optimize database queries
- [ ] Cache frequently accessed data
- [ ] Memory usage optimization

### Code Quality
- [ ] Documentation improvements
- [ ] Code refactoring
- [ ] Type hints implementation

### UI/UX
- [ ] Consistent UI
- [ ] Consistent error messages