// Copyright 2014 The Oppia Authors. All Rights Reserved.
//
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
//      http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS-IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.

/**
 * @fileoverview Unit test for DateTimeFormatService.
 */

// TODO(#7222): Remove the following block of unnnecessary imports once
// the code corresponding to the spec is upgraded to Angular 8.
import { UpgradedServices } from 'services/UpgradedServices';
// ^^^ This block is to be removed.

require('services/date-time-format.service.ts');

describe('Datetime Formatter', function() {
  beforeEach(angular.mock.module('oppia'));
  beforeEach(angular.mock.module('oppia', function($provide) {
    var ugs = new UpgradedServices();
    for (let [key, value] of Object.entries(ugs.upgradedServices)) {
      $provide.value(key, value);
    }
  }));

  describe('datetimeformatter', function() {
    // This corresponds to Fri, 21 Nov 2014 09:45:00 GMT.
    var NOW_MILLIS = 1416563100000;
    var df = null;
    var OldDate = Date;

    beforeEach(angular.mock.inject(function($injector) {
      df = $injector.get('DateTimeFormatService');

      // Mock Date() to give a time of NOW_MILLIS in GMT. (Unfortunately, there
      // doesn't seem to be a good way to set the timezone locale directly.)
      spyOn(window, 'Date').and.callFake(function() {
        return new OldDate(NOW_MILLIS);
      });
    }));

    it('should correctly indicate recency', function() {
      // 1 second ago is recent.
      expect(df.isRecent(NOW_MILLIS - 1)).toBe(true);
      // 72 hours ago is recent.
      expect(df.isRecent(NOW_MILLIS - 72 * 60 * 60 * 1000)).toBe(true);
      // 8 days ago is not recent.
      expect(df.isRecent(NOW_MILLIS - 8 * 24 * 60 * 60 * 1000)).toBe(false);
    });
  });
});
