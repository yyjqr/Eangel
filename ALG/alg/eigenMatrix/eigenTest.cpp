
#include<Eigen/Core>
#include<iostream>
using namespace std;
using namespace Eigen;
 
int main()
{
 
    MatrixXd::Index maxRow, maxCol;
	MatrixXd::Index minRow, minCol;
	MatrixXd mMat(4,4);
	mMat << 11, 10, 13, 15,
			3, 24, 56,	1,
			2, 12, 45,	0,
			8, 5,	6,	4;

	double min = mMat.minCoeff(&minRow,&minCol);
	double max = mMat.maxCoeff(&maxRow,&maxCol);
	cout << "Max = \n" << max << endl;
	cout << "Min = \n" << min << endl;
	cout << "minRow = " << minRow << "minCol = " <<minCol<<endl;
	cout << "maxRow = " << maxRow << "maxCol = " << maxCol << endl;
    MatrixXd mMatLarge(8,8);
    mMatLarge << mMat,MatrixXd::Zero(4,4),
                 MatrixXd::Zero(4,4),mMat ;
    cout  << "test mMatLarge:\n" <<mMatLarge;
	int stateSize = 8;
	Eigen::VectorXd veh_state(stateSize);
	for (int i = 0;i<2;i++)
	{
	   veh_state << 1, 2, 0, 0,4,i, 0, 0;
	   cout<<"\n line:"<< __LINE__<<"test Matrix" <<endl;
	}
	cout <<veh_state;
    return 0;
}
