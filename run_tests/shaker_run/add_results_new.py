custom_res1 = [{'status_id': 5, 'content': 'Check [Operations per second Median; iops]', 'expected': '88888', 'actual': '7777'},{'status_id': 5, 'content': 'Check [deviation; %]', 'expected': '5555', 'actual': '9999'}]
res1 = {'test_id': test_4kib_read, 'status_id': 5, 'custom_test_case_steps_results': custom_res1}
res2 = {'test_id': test_4kib_write, 'status_id': 5, 'custom_test_case_steps_results': [{'status_id': 5, 'content': 'Check [Operations per second Median; iops]', 'expected': '20202', 'actual': '30303'},{'status_id': 5, 'content': 'Check [deviation; %]', 'expected': '90909', 'actual': '80808'}]}
results_list = [res1, res2]
res_all = {'results': results_list}

print client.send_post('add_results/{}'.format(run_id), res_all)
